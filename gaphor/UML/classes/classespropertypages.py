from __future__ import annotations

import logging

from gi.repository import Gdk, Gtk

from gaphor import UML
from gaphor.core import gettext, transactional
from gaphor.core.format import format, parse
from gaphor.diagram.propertypages import (
    EditableTreeModel,
    PropertyPageBase,
    PropertyPages,
    help_link,
    NamePropertyPage,
    new_resource_builder,
    on_bool_cell_edited,
    on_text_cell_edited,
    unsubscribe_all_on_destroy,
)
from gaphor.UML.classes.datatype import DataTypeItem
from gaphor.UML.classes.interface import Folded, InterfaceItem
from gaphor.UML.classes.klass import ClassItem
from gaphor.UML.deployments.connector import ConnectorItem

log = logging.getLogger(__name__)


new_builder = new_resource_builder("gaphor.UML.classes")


@transactional
def on_keypress_event(ctrl, keyval, keycode, state, tree):
    k = Gdk.keyval_name(keyval).lower()
    if state & Gdk.ModifierType.CONTROL_MASK:
        return False

    if k in ("backspace", "delete"):
        model, iter = tree.get_selection().get_selected()
        if iter:
            model.remove(iter)
    elif k in ("equal", "plus"):
        model, iter = tree.get_selection().get_selected()
        model.swap(iter, model.iter_next(iter))
        return True
    elif k in ("minus", "underscore"):
        model, iter = tree.get_selection().get_selected()
        model.swap(iter, model.iter_previous(iter))
        return True
    return False


class ClassAttributes(EditableTreeModel):
    """GTK tree model to edit class attributes."""

    def __init__(self, item):
        super().__init__(item, cols=(str, bool, object))

    def get_rows(self):
        for attr in self._item.subject.ownedAttribute:
            if not attr.association:
                yield [format(attr, note=True), attr.isStatic, attr]

    def create_object(self):
        attr = self._item.model.create(UML.Property)
        self._item.subject.ownedAttribute = attr
        return attr

    @transactional
    def set_object_value(self, row, col, value):
        attr = row[-1]
        if col == 0:
            parse(attr, value)
            row[0] = format(attr, note=True)
        elif col == 1:
            attr.isStatic = not attr.isStatic
            row[1] = attr.isStatic
        elif col == 2:
            # Value in attribute object changed:
            row[0] = format(attr, note=True)
            row[1] = attr.isStatic

    def swap_objects(self, o1, o2):
        return self._item.subject.ownedAttribute.swap(o1, o2)

    def sync_model(self, new_order):
        self._item.subject.ownedAttribute.order(
            lambda e: new_order.index(e) if e in new_order else len(new_order)
        )


class ClassOperations(EditableTreeModel):
    """GTK tree model to edit class operations."""

    def __init__(self, item):
        super().__init__(item, cols=(str, bool, bool, object))

    def get_rows(self):
        for operation in self._item.subject.ownedOperation:
            yield [
                format(operation, note=True),
                operation.isAbstract,
                operation.isStatic,
                operation,
            ]

    def create_object(self):
        operation = self._item.model.create(UML.Operation)
        self._item.subject.ownedOperation = operation
        return operation

    @transactional
    def set_object_value(self, row, col, value):
        operation = row[-1]
        if col == 0:
            parse(operation, value)
            row[0] = format(operation, note=True)
        elif col == 1:
            operation.isAbstract = not operation.isAbstract
            row[1] = operation.isAbstract
        elif col == 2:
            operation.isStatic = not operation.isStatic
            row[2] = operation.isStatic
        elif col == 3:
            row[0] = format(operation, note=True)
            row[1] = operation.isAbstract
            row[2] = operation.isStatic

    def swap_objects(self, o1, o2):
        return self._item.subject.ownedOperation.swap(o1, o2)

    def sync_model(self, new_order):
        self._item.subject.ownedOperation.order(new_order.index)


class ClassEnumerationLiterals(EditableTreeModel):
    """GTK tree model to edit enumeration literals."""

    def __init__(self, item):
        super().__init__(item, cols=(str, object))

    def get_rows(self):
        for literal in self._item.subject.ownedLiteral:
            yield [format(literal), literal]

    def create_object(self):
        literal = self._item.model.create(UML.EnumerationLiteral)
        self._item.subject.ownedLiteral = literal
        literal.enumeration = self._item.subject
        return literal

    @transactional
    def set_object_value(self, row, col, value):
        literal = row[-1]
        if col == 0:
            parse(literal, value)
            row[0] = format(literal)
        elif col == 1:
            # Value in attribute object changed:
            row[0] = format(literal)

    def swap_objects(self, o1, o2):
        return self._item.subject.ownedLiteral.swap(o1, o2)

    def sync_model(self, new_order):
        self._item.subject.ownedLiteral.order(new_order.index)


def tree_view_column_tooltips(tree_view, tooltips):
    assert tree_view.get_n_columns() == len(tooltips)

    def on_query_tooltip(widget, x, y, keyboard_mode, tooltip):
        if path_and_more := widget.get_path_at_pos(x, y):
            path, column, cx, cy = path_and_more
            n = widget.get_columns().index(column)
            if tooltips[n]:
                tooltip.set_text(tooltips[n])
                return True
        return False

    tree_view.connect("query-tooltip", on_query_tooltip)


@PropertyPages.register(UML.NamedElement)
class NamedElementPropertyPage(NamePropertyPage):
    """An adapter which works for any named item view.

    It also sets up a table view which can be extended.
    """

    order = 10

    def __init__(self, subject: UML.NamedElement | None):
        super().__init__(subject)

    def construct(self):
        if (
            not self.subject
            or UML.recipes.is_metaclass(self.subject)
            or isinstance(self.subject, UML.ActivityPartition)
        ):
            return

        return super().construct()


@PropertyPages.register(UML.Classifier)
class ClassifierPropertyPage(PropertyPageBase):
    order = 15

    def __init__(self, subject):
        self.subject = subject

    def construct(self):
        if UML.recipes.is_metaclass(self.subject):
            return

        builder = new_builder(
            "classifier-editor",
            signals={"abstract-changed": (self._on_abstract_change,)},
        )

        abstract = builder.get_object("abstract")
        abstract.set_active(self.subject.isAbstract)

        return builder.get_object("classifier-editor")

    @transactional
    def _on_abstract_change(self, button, gparam):
        self.subject.isAbstract = button.get_active()


@PropertyPages.register(InterfaceItem)
class InterfacePropertyPage(PropertyPageBase):
    """Adapter which shows a property page for an interface view."""

    order = 15

    def __init__(self, item):
        self.item = item

    def construct(self):
        builder = new_builder(
            "interface-editor", signals={"folded-changed": (self._on_fold_change,)}
        )

        item = self.item

        connected_items = [
            c.item for c in item.diagram.connections.get_connections(connected=item)
        ]
        disallowed = (ConnectorItem,)
        can_fold = not any(isinstance(i, disallowed) for i in connected_items)

        folded = builder.get_object("folded")
        folded.set_active(item.folded != Folded.NONE)
        folded.set_sensitive(can_fold)

        return builder.get_object("interface-editor")

    @transactional
    def _on_fold_change(self, button, gparam):
        item = self.item

        fold = button.get_active()

        item.folded = Folded.PROVIDED if fold else Folded.NONE


@PropertyPages.register(DataTypeItem)
@PropertyPages.register(ClassItem)
@PropertyPages.register(InterfaceItem)
class AttributesPage(PropertyPageBase):
    """An editor for attributes associated with classes and interfaces."""

    order = 20

    def __init__(self, item):
        super().__init__()
        self.item = item
        self.watcher = item.subject and item.subject.watcher()

    def construct(self):
        if not self.item.subject:
            return

        self.model = ClassAttributes(self.item)

        builder = new_builder(
            "attributes-editor",
            "attributes-info",
            "static-label",
            signals={
                "show-attributes-changed": (self._on_show_attributes_change,),
                "attributes-name-edited": (on_text_cell_edited, self.model, 0),
                "attributes-static-edited": (on_bool_cell_edited, self.model, 1),
                "attributes-info-clicked": (self.on_attributes_info_clicked),
            },
        )
        self.info = builder.get_object("attributes-info")
        help_link(builder, "attributes-info-icon", "attributes-info")

        show_attributes = builder.get_object("show-attributes")
        show_attributes.set_active(self.item.show_attributes)

        tree_view: Gtk.TreeView = builder.get_object("attributes-list")
        tree_view.set_model(self.model)
        tree_view_column_tooltips(tree_view, ["", gettext("Static")])
        controller = Gtk.EventControllerKey.new()
        tree_view.add_controller(controller)
        controller.connect("key-pressed", on_keypress_event, tree_view)

        def handler(event):
            attribute = event.element
            for row in self.model:
                if row[-1] is attribute:
                    row[:] = [
                        format(attribute, note=True),
                        attribute.isStatic,
                        attribute,
                    ]

        self.watcher.watch("ownedAttribute.name", handler).watch(
            "ownedAttribute.isDerived", handler
        ).watch("ownedAttribute.visibility", handler).watch(
            "ownedAttribute.isStatic", handler
        ).watch(
            "ownedAttribute.lowerValue", handler
        ).watch(
            "ownedAttribute.upperValue", handler
        ).watch(
            "ownedAttribute.defaultValue", handler
        ).watch(
            "ownedAttribute.typeValue", handler
        )

        return unsubscribe_all_on_destroy(
            builder.get_object("attributes-editor"), self.watcher
        )

    @transactional
    def _on_show_attributes_change(self, button, gparam):
        self.item.show_attributes = button.get_active()
        self.item.request_update()

    def on_attributes_info_clicked(self, image, event):
        self.info.show()


@PropertyPages.register(DataTypeItem)
@PropertyPages.register(ClassItem)
@PropertyPages.register(InterfaceItem)
class OperationsPage(PropertyPageBase):
    """An editor for operations associated with classes and interfaces."""

    order = 30

    def __init__(self, item):
        super().__init__()
        self.item = item
        self.watcher = item.subject and item.subject.watcher()

    def construct(self):
        if not self.item.subject:
            return

        self.model = ClassOperations(self.item)

        builder = new_builder(
            "operations-editor",
            "operations-info",
            "static-label",
            "abstract-label",
            signals={
                "show-operations-changed": (self._on_show_operations_change,),
                "operations-name-edited": (on_text_cell_edited, self.model, 0),
                "operations-abstract-edited": (on_bool_cell_edited, self.model, 1),
                "operations-static-edited": (on_bool_cell_edited, self.model, 2),
                "operations-info-clicked": (self.on_operations_info_clicked),
            },
        )

        self.info = builder.get_object("operations-info")
        help_link(builder, "operations-info-icon", "operations-info")

        show_operations = builder.get_object("show-operations")
        show_operations.set_active(self.item.show_operations)

        tree_view: Gtk.TreeView = builder.get_object("operations-list")
        tree_view.set_model(self.model)
        tree_view_column_tooltips(
            tree_view, ["", gettext("Abstract"), gettext("Static")]
        )
        controller = Gtk.EventControllerKey.new()
        tree_view.add_controller(controller)
        controller.connect("key-pressed", on_keypress_event, tree_view)

        def handler(event):
            operation = event.element
            for row in self.model:
                if row[-1] is operation:
                    row[:] = [
                        format(operation, note=True),
                        operation.isAbstract,
                        operation.isStatic,
                        operation,
                    ]

        self.watcher.watch("ownedOperation.name", handler).watch(
            "ownedOperation.isAbstract", handler
        ).watch("ownedOperation.visibility", handler).watch(
            "ownedOperation.ownedParameter.lowerValue", handler
        ).watch(
            "ownedOperation.ownedParameter.upperValue", handler
        ).watch(
            "ownedOperation.ownedParameter.typeValue", handler
        ).watch(
            "ownedOperation.ownedParameter.defaultValue", handler
        )

        return unsubscribe_all_on_destroy(
            builder.get_object("operations-editor"), self.watcher
        )

    @transactional
    def _on_show_operations_change(self, button, gparam):
        self.item.show_operations = button.get_active()
        self.item.request_update()

    def on_operations_info_clicked(self, image, event):
        self.info.show()


@PropertyPages.register(UML.Component)
class ComponentPropertyPage(PropertyPageBase):
    order = 15

    subject: UML.Component

    def __init__(self, subject):
        self.subject = subject

    def construct(self):
        subject = self.subject

        if not subject:
            return

        builder = new_builder(
            "component-editor",
            signals={"indirectly-instantiated-changed": (self._on_ii_change,)},
        )

        ii = builder.get_object("indirectly-instantiated")
        ii.set_active(subject.isIndirectlyInstantiated)

        return builder.get_object("component-editor")

    @transactional
    def _on_ii_change(self, button, gparam):
        """Called when user clicks "Indirectly instantiated" check button."""
        if subject := self.subject:
            subject.isIndirectlyInstantiated = button.get_active()
