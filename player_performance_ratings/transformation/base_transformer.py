from abc import abstractmethod, ABC

import pandas as pd


class BaseTransformer(ABC):

    @abstractmethod
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        pass

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        pass

    @property
    @abstractmethod
    def features_created(self) -> list[str]:
        pass


