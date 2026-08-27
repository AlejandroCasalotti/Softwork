from abc import ABC, abstractmethod


class BaseOdooAdapter(ABC):
    @abstractmethod
    def test_connection(self):
        raise NotImplementedError

    @abstractmethod
    def read(self, model, ids, fields=None):
        raise NotImplementedError

    @abstractmethod
    def search(self, model, domain=None, offset=0, limit=None, order=None):
        raise NotImplementedError

    @abstractmethod
    def search_read(self, model, domain=None, fields=None, offset=0, limit=None, order=None):
        raise NotImplementedError

    @abstractmethod
    def create(self, model, values):
        raise NotImplementedError

    @abstractmethod
    def write(self, model, ids, values):
        raise NotImplementedError

    @abstractmethod
    def unlink(self, model, ids):
        raise NotImplementedError

    @abstractmethod
    def execute(self, model, method, args=None, kwargs=None):
        raise NotImplementedError

    @abstractmethod
    def metadata(self, model):
        raise NotImplementedError
