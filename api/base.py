from abc import ABC, abstractmethod
import pandas as pd

class BaseOptionExchange(ABC):
    @abstractmethod
    def get_btc_price(self) -> float:
        pass

    @abstractmethod
    def load_options(self) -> pd.DataFrame:
        pass