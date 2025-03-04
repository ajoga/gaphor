from pytest_archon import archrule

import gaphor
from gaphor.entrypoint import load_entry_points

GAPHOR_CORE = [
    "gaphor.core*",
    "gaphor.abc",
    "gaphor.action",
    "gaphor.entrypoint",
    "gaphor.i18n",
    "gaphor.transaction",
    "gaphor.event",
]

UI_LIBRARIES = [
    "gi.repository.Adw",
    "gi.repository.Gdk",
    "gi.repository.Gtk",
]


def test_core_packages():
    (
        archrule("gaphor.core does not depend on the rest of the system")
        .match("gaphor.core*")
        .exclude("*.tests.*")
        .may_import(*GAPHOR_CORE)
        .should_not_import("gaphor*")
        .should_not_import(*UI_LIBRARIES)
        .check(gaphor, skip_type_checking=True)
    )


def test_diagram_package():
    # NB. gaphor.diagram.tools.dropzone includes gaphor.UML.recipes,
    # so it can assign the right owner package to a newly created element.
    (
        archrule("Diagrams are part of the core")
        .match("gaphor.diagram*")
        .exclude("*.tests.*")
        .may_import(*GAPHOR_CORE)
        .may_import("gaphor.diagram*")
        .may_import("gaphor.UML.recipes")
        .may_import("gaphor.UML.uml")
        .should_not_import("gaphor*")
        .check(gaphor)
    )

    (
        archrule("GTK dependencies")
        .match("gaphor.diagram*")
        .exclude("*.tests.*")
        .exclude("gaphor.diagram.general.uicomponents")
        .exclude("gaphor.diagram.tools*")
        .exclude("gaphor.diagram.*editors")
        .exclude("gaphor.diagram.*propertypages")
        .should_not_import(*UI_LIBRARIES)
        .check(gaphor)
    )


def test_services_package():
    (
        archrule("Services only depend on core functionality")
        .match("gaphor.services*")
        .exclude("*.tests.*")
        .may_import(*GAPHOR_CORE)
        .may_import("gaphor.diagram*")
        .may_import("gaphor.services*")
        .should_not_import("gaphor*")
        .should_not_import(*UI_LIBRARIES)
        .check(gaphor)
    )


def test_storage_package():
    (
        archrule("Storage only depends on core functionality")
        .match("gaphor.storage*")
        .exclude("*.tests.*")
        .may_import(*GAPHOR_CORE)
        .may_import("gaphor.diagram*")
        .may_import("gaphor.storage*")
        .may_import("gaphor.application", "gaphor.services.componentregistry")
        .should_not_import("gaphor*")
        .should_not_import(*UI_LIBRARIES)
        .check(gaphor)
    )


def test_modeling_languages_should_not_depend_on_ui_package():
    (
        archrule("Modeling languages should not depend on the UI package")
        .match("gaphor.C4Model*", "gaphor.RAAML*", "gaphor.SysML*", "gaphor.UML*")
        .should_not_import("gaphor.ui*")
        .check(gaphor)
    )


def test_moduling_languages_should_initialize_without_gtk():
    modeling_languages: list[str] = [
        c.__module__ for c in load_entry_points("gaphor.modelinglanguages").values()
    ]
    assert modeling_languages

    (
        archrule("No GTK dependency for modeling languages")
        .match(*modeling_languages)
        .should_not_import(*UI_LIBRARIES)
        .check(gaphor)
    )


def test_uml_package_does_not_depend_on_other_modeling_languages():
    (
        archrule("No modeling language dependencies for UML")
        .match("gaphor.UML*")
        .exclude("*.tests.*")
        .should_not_import("gaphor.C4Model*", "gaphor.RAAML*", "gaphor.SysML*")
        .check(gaphor, only_toplevel_imports=True)
    )
