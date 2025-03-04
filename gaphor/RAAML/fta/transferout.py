"""Transfer Out item definition."""

from gaphas.geometry import Rectangle

from gaphor.core.modeling import DrawContext
from gaphor.diagram.presentation import (
    Classified,
    ElementPresentation,
    from_package_str,
)
from gaphor.diagram.shapes import Box, IconBox, Text, stroke
from gaphor.diagram.support import represents
from gaphor.diagram.text import FontStyle, FontWeight
from gaphor.RAAML import raaml
from gaphor.RAAML.fta.constants import DEFAULT_FTA_MAJOR
from gaphor.RAAML.fta.transferin import draw_transfer_in
from gaphor.UML.recipes import stereotypes_str


@represents(raaml.TransferOut)
class TransferOutItem(Classified, ElementPresentation):
    def __init__(self, diagram, id=None):
        super().__init__(diagram, id, width=DEFAULT_FTA_MAJOR, height=DEFAULT_FTA_MAJOR)

        self.watch("subject[NamedElement].name").watch(
            "subject[NamedElement].namespace.name"
        )

    def update_shapes(self, event=None):
        self.shape = IconBox(
            Box(
                draw=draw_transfer_out,
            ),
            Text(
                text=lambda: stereotypes_str(
                    self.subject, [self.diagram.gettext("Transfer Out")]
                ),
            ),
            Text(
                text=lambda: self.subject.name or "",
                width=lambda: self.width - 4,
                style={
                    "font-weight": FontWeight.BOLD,
                    "font-style": FontStyle.NORMAL,
                },
            ),
            Text(
                text=lambda: from_package_str(self),
                style={"font-size": "x-small"},
            ),
        )


def draw_transfer_out(box, context: DrawContext, bounding_box: Rectangle):
    draw_transfer_in(box, context, bounding_box)
    cr = context.cairo
    cr.move_to(bounding_box.width / 4.0, bounding_box.height / 2.0)
    cr.line_to(0, bounding_box.height / 2.0)
    stroke(context)
