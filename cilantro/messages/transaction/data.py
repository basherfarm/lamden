from cilantro.messages.base.base import MessageBase
from cilantro.messages.transaction.contract import ContractTransaction
from cilantro.utils.lazy_property import lazy_property
from cilantro.utils.hasher import Hasher
from enum import Enum, auto
import capnp
import transaction_capnp

class Status(Enum):
    SUCCESS = auto()
    FAILURE = auto()

class TransactionData(MessageBase):

    def validate(self):
        self.contract_tx

    @classmethod
    def _deserialize_data(cls, data: bytes):
        return transaction_capnp.TransactionData.from_bytes_packed(data)

    @classmethod
    def create(cls, contract_tx: ContractTransaction, status: str, state: str):
        assert issubclass(type(contract_tx), ContractTransaction), "contract_tx must be of type ContractTransaction"
        assert type(contract_tx) in MessageBase.registry, "MessageBase class {} not found in registry {}"\
            .format(type(contract_tx), MessageBase.registry)

        data = transaction_capnp.TransactionData.new_message()
        data.contractTransaction = contract_tx._data
        data.status = Status[status].value
        data.state = state

        return cls(data)

    @lazy_property
    def contract_tx(self) -> ContractTransaction:
        return ContractTransaction.from_data(self._data.contractTransaction)

    @property
    def status(self) -> str:
        return Status(self._data.status).name

    @property
    def state(self) -> str:
        return self._data.state

    @lazy_property
    def hash(self):
        return Hasher.hash(self.contract_tx.__str__() + Status(self._data.status).name + self._data.state)

    def __hash__(self):
        return int(self.hash, 16)