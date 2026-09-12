from abc import ABC, abstractmethod


class BaseOdooAdapter(ABC):
    @abstractmethod
    def test_connection(self):
        raise NotImplementedError

    @abstractmethod
    def read(self, model, ids, fields=None, context=None):
        raise NotImplementedError

    @abstractmethod
    def search(self, model, domain=None, offset=0, limit=None, order=None, context=None):
        raise NotImplementedError

    @abstractmethod
    def search_read(self, model, domain=None, fields=None, offset=0, limit=None, order=None, context=None):
        raise NotImplementedError

    @abstractmethod
    def metadata(self, model):
        raise NotImplementedError

    @abstractmethod
    def current_user_context(self):
        raise NotImplementedError


class WriteCapableOdooAdapter(BaseOdooAdapter):
    @abstractmethod
    def create(self, model, values, context=None):
        raise NotImplementedError

    @abstractmethod
    def write(self, model, ids, values, context=None):
        raise NotImplementedError

    @abstractmethod
    def unlink(self, model, ids):
        raise NotImplementedError

    @abstractmethod
    def execute(self, model, method, args=None, kwargs=None):
        raise NotImplementedError
