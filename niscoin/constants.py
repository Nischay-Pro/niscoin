from enum import Enum


class Award(Enum):
    FIRST = "🥇"
    SECOND = "🥈"
    THIRD = "🥉"

    def __str__(self):
        return str(self.value)


class Reputation(Enum):
    MININEGATIVE = -0.5
    NEGATIVE = -1
    MEGANEGATIVE = -2
    MINIPOSITIVE = 0.5
    POSITIVE = 1
    MEGAPOSITIVE = 2


class CliStoreType(Enum):
    ODDS = "odds"
    MULTIPLIER = "multiplier"
    EXCHANGE = "exchange"
    TRANSLATION = "translation"
