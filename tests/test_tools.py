from datetime import datetime

from agent.tools import calculator, get_current_time


def test_calculator_multiplies_numbers() -> None:
    result = calculator.invoke(
        {
            "a": 6,
            "b": 7,
            "operation": "multiply",
        }
    )

    assert result == "计算结果为：42"


def test_current_time_uses_expected_format() -> None:
    result = get_current_time.invoke({})

    parsed = datetime.strptime(
        result,
        "%Y-%m-%d %H:%M:%S",
    )

    assert isinstance(parsed, datetime)
