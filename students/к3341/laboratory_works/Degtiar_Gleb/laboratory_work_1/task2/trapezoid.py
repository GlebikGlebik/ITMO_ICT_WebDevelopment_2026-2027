def trapezoid(a: float, b: float, h: float) -> str:
    if a <= 0 or b <= 0 or h <= 0:
        raise ValueError("Основания и высота должны быть положительными")
    return f"Площадь трапеции S = (({a:g} + {b:g}) / 2) * {h:g} = {(a + b) / 2 * h:.4f}"

operation = ("Площадь трапеции", ["основание a", "основание b", "высота h"], trapezoid)

NAME, PARAMS, FUNC = operation