# stdlib
import copy
from typing import Any, Callable, List, Optional

# third party
import numpy as np
import pandas as pd

# adjutorium absolute
from adjutorium.plugins.explainers.base import ExplainerPlugin
from adjutorium.utils.pip import install

for retry in range(2):
    try:
        # third party
        from symbolic_pursuit.models import SymbolicRegressor

        break
    except ImportError:
        depends = ["symbolic_pursuit"]
        install(depends)


class SymbolicPursuitPlugin(ExplainerPlugin):
    """
    Interpretability plugin based on Symbolic Pursuit.

    Based on the NeurIPS 2020 paper "Learning outside the black-box: at the pursuit of interpretable models".

    Args:
        estimator: model. The model to explain.
        X: dataframe. Training set
        y: dataframe. Training labels
        task_type: str. classification or risk_estimation
        prefit: bool. If true, the estimator won't be trained.
        n_epoch: int. training epochs
        subsample: int. Number of samples to use.
        time_to_event: dataframe. Used for risk estimation tasks.
        eval_times: list. Used for risk estimation tasks.
        loss_tol: float. The tolerance for the loss under which the pursuit stops
        ratio_tol: float. A new term is added only if new_loss / old_loss < ratio_tol
        maxiter: float.  Maximum number of iterations for optimization
        eps: float. Number used for numerical stability
        random_seed: float. Random seed for reproducibility
    """

    def __init__(
        self,
        estimator: Any,
        X: pd.DataFrame,
        y: pd.DataFrame,
        task_type: str = "classification",
        feature_names: Optional[List] = None,
        subsample: int = 10,
        prefit: bool = False,
        n_epoch: int = 10000,
        # risk estimation
        time_to_event: Optional[pd.DataFrame] = None,  # for survival analysis
        eval_times: Optional[List] = None,  # for survival analysis
        # symbolic pursuit params
        loss_tol: float = 1.0e-3,
        ratio_tol: float = 0.9,
        maxiter: int = 100,
        eps: float = 1.0e-5,
        random_seed: int = 0,
        patience: int = 10,
    ) -> None:
        if task_type not in ["classification", "risk_estimation", "regression"]:
            raise RuntimeError("invalid task type")

        self.feature_names = (
            feature_names if feature_names is not None else pd.DataFrame(X).columns
        )

        X = pd.DataFrame(X, columns=self.feature_names)
        model = copy.deepcopy(estimator)

        self.task_type = task_type
        self.loss_tol = loss_tol
        self.ratio_tol = ratio_tol
        self.maxiter = maxiter
        self.eps = eps
        self.random_seed = random_seed

        std_args = {
            "loss_tol": loss_tol,
            "ratio_tol": ratio_tol,
            "random_seed": random_seed,
            "maxiter": maxiter,
            "patience": patience,
        }

        if task_type == "classification":
            if not prefit:
                model.fit(X, y)

            self.explainer = SymbolicRegressor(
                **std_args,
                task_type="classification",
            )
            self.explainer.fit(model.predict, X)
        elif task_type == "regression":
            if not prefit:
                model.fit(X, y)

            self.explainer = SymbolicRegressor(
                **std_args,
                task_type="regression",
            )
            self.explainer.fit(model.predict, X)
        elif task_type == "risk_estimation":
            if time_to_event is None or eval_times is None:
                raise RuntimeError("Invalid input for risk estimation interpretability")

            if not prefit:
                model.fit(X, time_to_event, y)

            def model_fn_factory(horizon: int) -> Callable:
                def model_fn(X: pd.DataFrame) -> pd.DataFrame:
                    out = np.asarray(model.predict(X, [horizon])).squeeze()

                    return out

                return model_fn

            self.explainer = SymbolicRegressor(
                **std_args,
                task_type="classification",
            )
            self.explainer.fit(model_fn_factory(eval_times[-1]), X)

    def explain(self, X: pd.DataFrame) -> np.ndarray:
        X = pd.DataFrame(X, columns=self.feature_names)

        results = []
        for idx, row in X.iterrows():
            results.append(self.explainer.get_feature_importance(row.values))

        return np.asarray(results)

    def plot(self, X: pd.DataFrame) -> tuple:  # type: ignore
        return str(self.explainer), self.explainer.get_projections()

    @staticmethod
    def name() -> str:
        return "symbolic_pursuit"

    @staticmethod
    def pretty_name() -> str:
        return "Symbolic Pursuit"


plugin = SymbolicPursuitPlugin
