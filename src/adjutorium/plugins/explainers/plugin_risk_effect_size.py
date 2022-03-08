# stdlib
import copy
from typing import Any, List, Optional

# third party
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# adjutorium absolute
from adjutorium.plugins.explainers.base import ExplainerPlugin


class RiskEffectSizePlugin(ExplainerPlugin):
    """
    Interpretability plugin based on Risk Effect size and Cohen's D.

    Args:
        estimator: model. The model to explain.
        X: dataframe. Training set
        y: dataframe. Training labels
        task_type: str. classification or risk_estimation
        prefit: bool. If true, the estimator won't be trained.
        n_epoch: int. training epochs
        time_to_event: dataframe. Used for risk estimation tasks.
        eval_times: list. Used for risk estimation tasks.
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
        effect_size: float = 0.5,
        # risk estimation
        time_to_event: Optional[pd.DataFrame] = None,  # for survival analysis
        eval_times: Optional[List] = None,  # for survival analysis
    ) -> None:
        if task_type not in ["classification", "risk_estimation"]:
            raise RuntimeError("invalid task type")

        self.feature_names = (
            feature_names if feature_names is not None else pd.DataFrame(X).columns
        )

        X = pd.DataFrame(X, columns=self.feature_names)
        model = copy.deepcopy(estimator)
        self.task_type = task_type
        self.effect_size = effect_size

        if task_type == "classification":
            if not prefit:
                model.fit(X, y)

            def model_fn(X: pd.DataFrame) -> pd.DataFrame:
                risk_prob = model.predict_proba(X).values[:, 1]
                return pd.DataFrame(risk_prob)

            self.predict_cbk = model_fn
        elif task_type == "risk_estimation":
            if time_to_event is None or eval_times is None:
                raise RuntimeError("Invalid input for risk estimation interpretability")

            if not prefit:
                model.fit(X, time_to_event, y)

            def model_fn(X: pd.DataFrame) -> pd.DataFrame:
                if eval_times is None:
                    raise RuntimeError(
                        "Invalid input for risk estimation interpretability"
                    )

                res = pd.DataFrame(model.predict(X, eval_times), columns=eval_times)

                return pd.DataFrame(res[eval_times[0]])

            self.predict_cbk = model_fn

    # function to calculate Cohen's d for independent samples
    def _cohend(self, d1: pd.DataFrame, d2: pd.DataFrame) -> pd.DataFrame:
        n1, n2 = len(d1), len(d2)
        # calculate the variance of the samples
        s1, s2 = np.var(d1, ddof=1), np.var(d2, ddof=1)
        # calculate the pooled standard deviation
        s = np.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))

        # calculate the means of the samples
        u1, u2 = np.mean(d1), np.mean(d2)
        # calculate the effect size
        return np.abs((u1 - u2) / s)

    def _get_population_shifts(
        self,
        predict_cbk: Any,
        X: pd.DataFrame,
    ) -> pd.DataFrame:
        def risk_to_cluster(row: pd.DataFrame) -> pd.DataFrame:
            output = row.copy()

            output[row < 0.2] = 0
            output[(row >= 0.2) & (row < 0.5)] = 1
            output[(row >= 0.5)] = 2

            return output

        training_preds = predict_cbk(X)
        buckets = training_preds.apply(risk_to_cluster)[training_preds.columns[0]]
        X = X.reset_index(drop=True)

        output = pd.DataFrame([], columns=X.columns)
        index = []
        for bucket in range(0, 4):
            curr_bucket = X[buckets == bucket]
            other_buckets = X[buckets > bucket]

            if len(curr_bucket) < 2 or len(other_buckets) < 2:
                continue

            diffs = self._cohend(curr_bucket, other_buckets).to_dict()

            heatmaps = pd.DataFrame([[0] * len(X.columns)], columns=X.columns)

            for key in diffs:
                if diffs[key] < self.effect_size:
                    continue

                heatmaps[key] = diffs[key]

            output = output.append(heatmaps)
            index.append(f"Risk lvl {bucket}")

        output.index = index
        output = output.astype(float)

        return output

    def plot(self, X: pd.DataFrame) -> None:  # type: ignore
        output = self._get_population_shifts(self.predict_cbk, X)
        thresh_line = [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]

        cols = output.columns
        cols = sorted(cols, key=lambda key: output[key].max(), reverse=True)

        output = output[cols]

        ignore_empty = []
        for col in output.columns:
            if output[col].sum() == 0:
                ignore_empty.append(col)
        output = output.drop(columns=ignore_empty)

        draw_lines = []
        thresh_iter = 0
        for idx, col in enumerate(output.columns):
            if (
                thresh_iter < len(thresh_line)
                and output[col].max() < thresh_line[thresh_iter]
            ):
                thresh_iter += 1
                draw_lines.append(idx)
        draw_lines.append(idx + 1)

        renamed_cols = {}
        for idx, col in enumerate(output.columns):
            renamed_cols[col] = f"{col} {idx}"

        output = output.rename(columns=renamed_cols)
        output = output.transpose()

        plt.figure(figsize=(4, int(len(output) * 0.5)))

        ax = sns.heatmap(
            output,
            cmap="Reds",
            linewidths=0.5,
            linecolor="black",
        )
        ax.xaxis.set_ticks_position("top")
        ax.hlines(draw_lines, *ax.get_ylim(), colors="blue")
        plt.show()

    def explain(self, X: pd.DataFrame) -> np.ndarray:
        X = pd.DataFrame(X, columns=self.feature_names)

        return self._get_population_shifts(self.predict_cbk, X)

    @staticmethod
    def name() -> str:
        return "risk_effect_size"

    @staticmethod
    def pretty_name() -> str:
        return "Risk Effect size"


plugin = RiskEffectSizePlugin