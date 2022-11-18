from model import Batch, OrderLine
from datetime import date
from typing import Tuple, Callable, TypeVar
from hypothesis import given, assume
from hypothesis.strategies import composite, text, integers, SearchStrategy

T = TypeVar('T')
Draw = TypeVar('Draw', bound=Callable[[SearchStrategy[T]], T])

OrderTestData = Tuple[Batch, OrderLine]

@composite
def _make_batch(draw: Draw, condition: Callable[[int, int], bool] = lambda x, y: True, batch_equal: bool = False) -> Tuple[Batch, OrderLine]:
    batch_id = draw(text(max_size=10))
    order_line = draw(text(max_size=10))
    eta = date.today() # TODO change this
    sku = draw(text(max_size=10))

    batch_qty = draw(integers(min_value=1, max_value=100_000))
    line_qty = draw(integers(min_value=1, max_value=100_000))

    if batch_equal:
        line_qty = batch_qty
    assume(condition(batch_qty, line_qty))

    batch = Batch(batch_id, sku, batch_qty, eta)
    line = OrderLine(order_line, sku, line_qty)
    
    return batch, line

    


def make_batch_and_line(sku: str, batch_qty: int, line_qty: int) -> Tuple[Batch, OrderLine]:
    return (
        Batch("batch-001", sku, batch_qty, eta=date.today()),
        OrderLine("order-123", sku, line_qty),
    )

def test_can_allocate_if_available_greater_than_required() -> None:
    large_batch, small_line = make_batch_and_line("ELEGANT-LAMP", 20, 2)
    assert large_batch.can_allocate(small_line)

@given(_make_batch(lambda batch_qty, line_qty: batch_qty > line_qty))
def test_can_allocate_if_available_greater_than_required_hyp(data: Tuple[Batch, OrderLine]) -> None:
    batch, orderline = data
    assert batch.can_allocate(orderline)
    

def test_cannot_allocate_if_available_smaller_than_required() -> None:
    small_batch, large_line = make_batch_and_line("ELEGANT-LAMP", 2, 20)
    assert small_batch.can_allocate(large_line) is False

@given(_make_batch(lambda batch_qty, line_qty: batch_qty < line_qty))
def test_cannot_allocate_if_available_smaller_than_required_hyp(data: OrderTestData) -> None:
    small_batch, large_line = data
    assert small_batch.can_allocate(large_line) is False

def test_can_allocate_if_available_equal_to_required() -> None:
    batch, line = make_batch_and_line("ELEGANT-LAMP", 2, 2)
    assert batch.can_allocate(line)

@given(_make_batch(batch_equal=True))
def test_can_allocate_if_available_equal_to_required_hyp(data: OrderTestData) -> None:
    batch, line = data
    assert batch.can_allocate(line)

@given(_make_batch(condition=lambda batch_qty, order_qty: batch_qty >= order_qty), text())
def test_cannot_allocate_if_skus_do_not_match(data: OrderTestData, new_sku: str) -> None:
    batch, old_line = data
    assume(batch.sku != new_sku)
    line = OrderLine(old_line.orderid, new_sku, old_line.qty)
    assert batch.can_allocate(line) is False

@given(_make_batch(condition=lambda batch_qty, order_qty: batch_qty >= order_qty))
def test_can_only_deallocate_allocated_lines(data: OrderTestData) -> None:
    batch, unallocated_line = data
    quantity = batch.available_quantity
    batch.deallocate(unallocated_line)
    assert batch.available_quantity == quantity # IdempotentA

@given(_make_batch(condition=lambda batch_qty, order_qty: batch_qty >= order_qty))
def test_allocation_is_idempotent(data: OrderTestData) -> None:
    batch, line = data
    final_quantity = batch.available_quantity - line.qty
    batch.allocate(line)
    batch.allocate(line)

    assert batch.available_quantity == final_quantity