# stdlib
from typing import Tuple

# third party
from lifelines.datasets import load_rossi
import numpy as np
import pytest
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split

# adjutorium absolute
from adjutorium.plugins.explainers.plugin_kernel_shap import plugin
from adjutorium.plugins.pipeline import Pipeline
from adjutorium.plugins.prediction.classifiers import Classifiers
from adjutorium.plugins.prediction.risk_estimation.plugin_cox_ph import plugin as CoxPH
from adjutorium.plugins.preprocessors import Preprocessors


def dataset() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    X, y = load_breast_cancer(return_X_y=True)
    return train_test_split(X, y, test_size=0.05)


@pytest.mark.slow
@pytest.mark.parametrize("classifier", ["logistic_regression", "xgboost"])
def test_plugin_sanity(classifier: str) -> None:
    X_train, X_test, y_train, y_test = dataset()

    template = Pipeline(
        [
            Preprocessors().get_type("minmax_scaler").fqdn(),
            Classifiers().get_type(classifier).fqdn(),
        ]
    )

    pipeline = template()

    explainer = plugin(
        pipeline, X_train, y_train, subsample=100, task_type="classification"
    )

    result = explainer.explain(X_test)

    assert len(result) == len(np.unique(y_train))
    assert len(result[0]) == len(X_test)


def test_plugin_name() -> None:
    assert plugin.name() == "kernel_shap"


@pytest.mark.slow
def test_plugin_kernel_shap_survival_prediction() -> None:
    rossi = load_rossi()

    X = rossi.drop(["week", "arrest"], axis=1)
    Y = rossi["arrest"]
    T = rossi["week"]

    surv = CoxPH().fit(X, T, Y)

    explainer = plugin(
        surv,
        X,
        Y,
        time_to_event=T,
        eval_times=[
            int(T[Y.iloc[:] == 1].quantile(0.50)),
            int(T[Y.iloc[:] == 1].quantile(0.75)),
        ],
        task_type="risk_estimation",
    )

    result = explainer.explain(X[:3])

    assert result.shape == (3, X.shape[1], 2)