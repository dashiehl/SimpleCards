from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSequentialAnimationGroup


def make_flip_animation(widget, on_midpoint) -> QSequentialAnimationGroup:
    """Scale-X 1->0 (edge-on), swap content via on_midpoint, then 0->1 back."""
    shrink = QPropertyAnimation(widget, b"flip_scale")
    shrink.setStartValue(1.0)
    shrink.setEndValue(0.0)
    shrink.setDuration(140)
    shrink.setEasingCurve(QEasingCurve.Type.InCubic)

    grow = QPropertyAnimation(widget, b"flip_scale")
    grow.setStartValue(0.0)
    grow.setEndValue(1.0)
    grow.setDuration(140)
    grow.setEasingCurve(QEasingCurve.Type.OutCubic)

    group = QSequentialAnimationGroup(widget)
    group.addAnimation(shrink)
    group.addAnimation(grow)
    shrink.finished.connect(on_midpoint)
    return group


def make_fade_slide_in(widget) -> QPropertyAnimation:
    anim = QPropertyAnimation(widget, b"windowOpacity")
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setDuration(200)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    return anim
