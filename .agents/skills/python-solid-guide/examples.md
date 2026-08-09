# Examples (Violation / Compliant)

## SRP

```python
# Violation — file I/O and ZIP in one type
class FileManager:
    def __init__(self, filename: str) -> None:
        self.path = Path(filename)

    def read(self) -> str:
        return self.path.read_text()

    def compress(self) -> None:
        with ZipFile(self.path.with_suffix('.zip'), 'w') as archive:
            archive.write(self.path)


# Compliant — separate change reasons
class FileManager:
    def __init__(self, filename: str) -> None:
        self.path = Path(filename)

    def read(self) -> str:
        return self.path.read_text()

    def write(self, data: str) -> None:
        self.path.write_text(data)


class ZipArchiver:
    def compress(self, path: Path) -> None:
        with ZipFile(path.with_suffix('.zip'), 'w') as archive:
            archive.write(path)
```

```python
# Violation — order + pay + notify
class FoodOrder:
    def create_order(self, details: dict) -> None: ...
    def process_payment(self, amount: float) -> None: ...
    def send_notification(self, message: str) -> None: ...


# Compliant
class FoodOrder:
    def create_order(self, details: dict) -> None: ...


class PaymentProcessor:
    def process_payment(self, amount: float) -> None: ...


class NotificationSender:
    def send_notification(self, message: str) -> None: ...
```

## OCP

```python
# Violation — new methods require editing this class
class DeliveryProcessor:
    def deliver(self, order_id: str, method: str) -> None:
        if method == 'post':
            print('post')
        elif method == 'email':
            print('email')
        # drone? another elif…


# Compliant — extend with new subclasses
class Delivery(ABC):
    @abstractmethod
    def deliver(self, order_id: str) -> None: ...


class PostDelivery(Delivery):
    def deliver(self, order_id: str) -> None:
        print(f'post {order_id}')


class EmailDelivery(Delivery):
    def deliver(self, order_id: str) -> None:
        print(f'email {order_id}')
```

```python
# Compliant strategy-style search (extend with new SearchBy types)
class SearchBy(ABC):
    @abstractmethod
    def is_matched(self, album: Album) -> bool: ...


class SearchByArtist(SearchBy):
    def __init__(self, artist: str) -> None:
        self._artist = artist

    def is_matched(self, album: Album) -> bool:
        return album.artist == self._artist


class AlbumBrowser:
    def browse(self, albums: list[Album], spec: SearchBy) -> list[Album]:
        return [a for a in albums if spec.is_matched(a)]
```

## LSP

```python
# Violation — subtype cannot honor base capability
class Bird:
    def fly(self) -> None:
        print('flapping')


class Ostrich(Bird):
    def fly(self) -> None:
        raise RuntimeError('ostriches do not fly')


# Compliant — shared base without false promises
class Bird(ABC):
    """A bird; not all birds fly."""


class FlyingBird(Bird):
    def fly(self) -> None:
        print('flapping')


class Ostrich(Bird):
    def run(self) -> None:
        print('running')
```

```python
# Violation — Square breaks Rectangle width/height independence
class Rectangle:
    def __init__(self, width: float, height: float) -> None:
        self._width = width
        self._height = height

    @property
    def width(self) -> float:
        return self._width

    @width.setter
    def width(self, value: float) -> None:
        self._width = value

    def area(self) -> float:
        return self._width * self._height


class Square(Rectangle):
    @Rectangle.width.setter
    def width(self, value: float) -> None:
        self._width = value
        self._height = value  # callers of Rectangle get surprised


# Compliant — do not force Square into mutable Rectangle hierarchy;
# share a Shape protocol instead.
class Shape(Protocol):
    def area(self) -> float: ...


class Rectangle:
    def __init__(self, width: float, height: float) -> None:
        self._width = width
        self._height = height

    def area(self) -> float:
        return self._width * self._height


class Square:
    def __init__(self, size: float) -> None:
        self._size = size

    def area(self) -> float:
        return self._size * self._size
```

## ISP

```python
# Violation — fat interface
class MultiFunctionDevice(ABC):
    @abstractmethod
    def print(self, document: str) -> None: ...

    @abstractmethod
    def scan(self, document: str) -> None: ...

    @abstractmethod
    def fax(self, document: str) -> None: ...


# Compliant — segregated roles
class Printer(ABC):
    @abstractmethod
    def print(self, document: str) -> None: ...


class Scanner(ABC):
    @abstractmethod
    def scan(self, document: str) -> None: ...


class OfficeCombo(Printer, Scanner):
    def print(self, document: str) -> None:
        print(f'print {document}')

    def scan(self, document: str) -> None:
        print(f'scan {document}')
```

```python
# Violation — one Payment with every rail
class Payment(ABC):
    @abstractmethod
    def pay_by_card(self, amount: float) -> None: ...

    @abstractmethod
    def pay_by_cash(self, amount: float) -> None: ...


# Compliant
class CardPayment(ABC):
    @abstractmethod
    def pay_by_card(self, amount: float) -> None: ...


class CashPayment(ABC):
    @abstractmethod
    def pay_by_cash(self, amount: float) -> None: ...
```

## DIP

```python
# Violation — high-level depends on concrete
class Invoice:
    def __init__(self) -> None:
        self._processor = CreditCardProcessor()

    def pay(self, amount: float) -> None:
        self._processor.process(amount)


# Compliant — depend on abstraction; inject detail
class PaymentProcessor(ABC):
    @abstractmethod
    def process(self, amount: float) -> None: ...


class CreditCardProcessor(PaymentProcessor):
    def process(self, amount: float) -> None:
        print(f'card {amount}')


class Invoice:
    def __init__(self, processor: PaymentProcessor) -> None:
        self._processor = processor

    def pay(self, amount: float) -> None:
        self._processor.process(amount)


# composition root / test seam
invoice = Invoice(CreditCardProcessor())
```

```python
# Compliant notification seam
class NotificationService(ABC):
    @abstractmethod
    def send(self, message: str) -> None: ...


class NotificationSender:
    def __init__(self, service: NotificationService) -> None:
        self._service = service

    def notify(self, message: str) -> None:
        self._service.send(message)
```
