# stdlib
from typing import Any, List

# autoprognosis absolute
import autoprognosis.plugins.core.params as params
import autoprognosis.plugins.imputers.base as base
from autoprognosis.utils.pip import install

for retry in range(2):
    try:
        # third party
        from hyperimpute.plugins.imputers.plugin_softimpute import plugin as base_model

        break
    except ImportError:
        depends = ["hyperimpute"]
        install(depends)


class SoftImputePlugin(base.ImputerPlugin):
    """Imputation plugin for completing missing values using the SoftImpute strategy.

    Method:
        Details in the SoftImpute class implementation.

    Example:
        >>> import numpy as np
        >>> from autoprognosis.plugins.imputers import Imputers
        >>> plugin = Imputers().get("softimpute")
        >>> plugin.fit_transform([[1, 1, 1, 1], [np.nan, np.nan, np.nan, np.nan], [1, 2, 2, 1], [2, 2, 2, 2]])
                      0             1             2             3
        0  1.000000e+00  1.000000e+00  1.000000e+00  1.000000e+00
        1  3.820605e-16  1.708249e-16  1.708249e-16  3.820605e-16
        2  1.000000e+00  2.000000e+00  2.000000e+00  1.000000e+00
        3  2.000000e+00  2.000000e+00  2.000000e+00  2.000000e+00
    """

    def __init__(self, random_state: int = 0, **kwargs: Any) -> None:
        model = base_model(random_state=random_state, **kwargs)

        super().__init__(model)

    @staticmethod
    def name() -> str:
        return base_model.name()

    @staticmethod
    def hyperparameter_space(*args: Any, **kwargs: Any) -> List[params.Params]:
        return base_model.hyperparameter_space()


plugin = SoftImputePlugin