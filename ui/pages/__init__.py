"""UI pages package for BPIC17 Event Log Analyzer."""

from ui.pages.case_explorer_page import CaseExplorerPage
from ui.pages.ex11_7_page import Ex11_7Page
from ui.pages.ex11_15_18_page import Ex11_15_18Page
from ui.pages.ex11_22_page import Ex11_22Page
from ui.pages.filter_page import FilterBuilderPage
from ui.pages.overview_page import OverviewPage

__all__ = [
    "OverviewPage",
    "Ex11_7Page",
    "Ex11_15_18Page",
    "Ex11_22Page",
    "CaseExplorerPage",
    "FilterBuilderPage",
]
