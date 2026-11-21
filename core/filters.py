"""Pure Python filtering engine for generic Disco-style log exploration.

Zero Qt/GUI imports are permitted in this module.
Supports 5 core filter types: Attribute, Endpoints, Performance, Follower, and Timeframe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import numpy as np
import pandas as pd

from core.metrics import compute_activity_frequency
from core.models import LoadedDataset, LogOverview


class FilterType(StrEnum):
    """Supported filter types matching Fluxicon Disco's taxonomy."""

    ATTRIBUTE = "Attribute"
    ENDPOINTS = "Endpoints"
    PERFORMANCE = "Performance"
    FOLLOWER = "Follower"
    TIMEFRAME = "Timeframe"


class FilterMode(StrEnum):
    """Case-level filtering operation mode."""

    KEEP_CASES = "KEEP_CASES"  # Keep cases matching the criteria
    DROP_CASES = "DROP_CASES"  # Discard cases matching the criteria


class FollowerType(StrEnum):
    """Relationship between two activities in a trace."""

    DIRECTLY_FOLLOWS = "DIRECTLY_FOLLOWS"  # Event B directly succeeds Event A
    EVENTUALLY_FOLLOWS = "EVENTUALLY_FOLLOWS"  # Event B appears anywhere after Event A


class TimeframeMode(StrEnum):
    """Time evaluation mode for Timeframe filter."""

    STARTED_IN_TIMEFRAME = "STARTED_IN_TIMEFRAME"
    COMPLETED_IN_TIMEFRAME = "COMPLETED_IN_TIMEFRAME"
    ACTIVE_IN_TIMEFRAME = "ACTIVE_IN_TIMEFRAME"


@dataclass
class BaseFilterRule:
    """Base dataclass for all filtering rules."""

    filter_type: FilterType
    mode: FilterMode = FilterMode.KEEP_CASES
    is_enabled: bool = True

    def describe(self) -> str:
        """Return a human-readable summary of this filter rule."""
        raise NotImplementedError


@dataclass
class AttributeFilterRule(BaseFilterRule):
    """Filter cases by values in an attribute (concept:name, org:resource, etc.)."""

    attribute_name: str = "concept:name"
    selected_values: tuple[str, ...] = ()

    def __init__(
        self,
        attribute_name: str = "concept:name",
        selected_values: tuple[str, ...] | list[str] = (),
        mode: FilterMode = FilterMode.KEEP_CASES,
        is_enabled: bool = True,
    ) -> None:
        super().__init__(filter_type=FilterType.ATTRIBUTE, mode=mode, is_enabled=is_enabled)
        self.attribute_name = attribute_name
        self.selected_values = tuple(selected_values)

    def describe(self) -> str:
        action = "Keep" if self.mode == FilterMode.KEEP_CASES else "Drop"
        attr_label = "Aktivitas" if self.attribute_name == "concept:name" else self.attribute_name
        vals = ", ".join(self.selected_values[:3])
        if len(self.selected_values) > 3:
            vals += f" (+{len(self.selected_values) - 3} lainnya)"
        return f"{action} cases containing {attr_label}: [{vals}]"


@dataclass
class EndpointsFilterRule(BaseFilterRule):
    """Filter cases by start activity (first_activity) or end activity (last_activity)."""

    start_activities: tuple[str, ...] = ()
    end_activities: tuple[str, ...] = ()

    def __init__(
        self,
        start_activities: tuple[str, ...] | list[str] = (),
        end_activities: tuple[str, ...] | list[str] = (),
        mode: FilterMode = FilterMode.KEEP_CASES,
        is_enabled: bool = True,
    ) -> None:
        super().__init__(filter_type=FilterType.ENDPOINTS, mode=mode, is_enabled=is_enabled)
        self.start_activities = tuple(start_activities)
        self.end_activities = tuple(end_activities)

    def describe(self) -> str:
        parts: list[str] = []
        if self.start_activities:
            parts.append(f"Mulai: [{', '.join(self.start_activities)}]")
        if self.end_activities:
            parts.append(f"Berakhir: [{', '.join(self.end_activities)}]")
        action = "Keep" if self.mode == FilterMode.KEEP_CASES else "Drop"
        return f"{action} cases with Endpoints: {' & '.join(parts)}"


@dataclass
class PerformanceFilterRule(BaseFilterRule):
    """Filter cases by duration (cycle_time_days)."""

    min_days: float = 0.0
    max_days: float = float("inf")

    def __init__(
        self,
        min_days: float = 0.0,
        max_days: float = float("inf"),
        mode: FilterMode = FilterMode.KEEP_CASES,
        is_enabled: bool = True,
    ) -> None:
        super().__init__(filter_type=FilterType.PERFORMANCE, mode=mode, is_enabled=is_enabled)
        self.min_days = max(0.0, float(min_days))
        self.max_days = float(max_days)

    def describe(self) -> str:
        action = "Keep" if self.mode == FilterMode.KEEP_CASES else "Drop"
        if np.isinf(self.max_days):
            return f"{action} cases with Durasi >= {self.min_days:.2f} hari"
        return f"{action} cases with Durasi: {self.min_days:.2f} s/d {self.max_days:.2f} hari"


@dataclass
class FollowerFilterRule(BaseFilterRule):
    """Filter cases where activity A is followed by activity B."""

    source_activity: str = ""
    target_activity: str = ""
    follower_type: FollowerType = FollowerType.EVENTUALLY_FOLLOWS

    def __init__(
        self,
        source_activity: str,
        target_activity: str,
        follower_type: FollowerType = FollowerType.EVENTUALLY_FOLLOWS,
        mode: FilterMode = FilterMode.KEEP_CASES,
        is_enabled: bool = True,
    ) -> None:
        super().__init__(filter_type=FilterType.FOLLOWER, mode=mode, is_enabled=is_enabled)
        self.source_activity = source_activity
        self.target_activity = target_activity
        self.follower_type = follower_type

    def describe(self) -> str:
        action = "Keep" if self.mode == FilterMode.KEEP_CASES else "Drop"
        rel = (
            "langsung diikuti"
            if self.follower_type == FollowerType.DIRECTLY_FOLLOWS
            else "kemudian diikuti"
        )
        return f"{action} cases: [{self.source_activity}] {rel} [{self.target_activity}]"


@dataclass
class TimeframeFilterRule(BaseFilterRule):
    """Filter cases by timestamp boundaries."""

    start_time_utc: datetime | None = None
    end_time_utc: datetime | None = None
    timeframe_mode: TimeframeMode = TimeframeMode.ACTIVE_IN_TIMEFRAME

    def __init__(
        self,
        start_time_utc: datetime | None = None,
        end_time_utc: datetime | None = None,
        timeframe_mode: TimeframeMode = TimeframeMode.ACTIVE_IN_TIMEFRAME,
        mode: FilterMode = FilterMode.KEEP_CASES,
        is_enabled: bool = True,
    ) -> None:
        super().__init__(filter_type=FilterType.TIMEFRAME, mode=mode, is_enabled=is_enabled)
        self.start_time_utc = start_time_utc
        self.end_time_utc = end_time_utc
        self.timeframe_mode = timeframe_mode

    def describe(self) -> str:
        action = "Keep" if self.mode == FilterMode.KEEP_CASES else "Drop"
        st = self.start_time_utc.strftime("%Y-%m-%d") if self.start_time_utc else "Awal"
        et = self.end_time_utc.strftime("%Y-%m-%d") if self.end_time_utc else "Akhir"
        return f"{action} cases in Timeframe ({st} s/d {et}) [{self.timeframe_mode.value}]"


@dataclass(frozen=True)
class FilterStepSummary:
    """Summary of data reduction at a specific filter step."""

    step_index: int
    rule_description: str
    is_enabled: bool
    cases_before: int
    cases_after: int
    events_after: int
    case_retention_pct: float


# ==============================================================================
# Filter Evaluation Engine (Pure Vectorized Pandas / NumPy)
# ==============================================================================


def evaluate_attribute_filter(
    raw_df: pd.DataFrame,
    case_summary_df: pd.DataFrame,
    rule: AttributeFilterRule,
) -> set[str]:
    """Find case IDs matching the attribute filter criteria."""
    if not rule.selected_values or raw_df.empty:
        return set()

    attr = rule.attribute_name
    if attr not in raw_df.columns:
        return set()

    matching_rows = raw_df[raw_df[attr].isin(rule.selected_values)]
    matching_cases: set[str] = set(matching_rows["case:concept:name"].dropna().unique())
    return matching_cases


def evaluate_endpoints_filter(
    case_summary_df: pd.DataFrame,
    rule: EndpointsFilterRule,
) -> set[str]:
    """Find case IDs matching start/end activity criteria."""
    if case_summary_df.empty:
        return set()

    mask = pd.Series(True, index=case_summary_df.index)

    if rule.start_activities:
        mask &= case_summary_df["first_activity"].isin(rule.start_activities)

    if rule.end_activities:
        mask &= case_summary_df["last_activity"].isin(rule.end_activities)

    return set(case_summary_df.loc[mask, "case_id"].dropna().unique())


def evaluate_performance_filter(
    case_summary_df: pd.DataFrame,
    rule: PerformanceFilterRule,
) -> set[str]:
    """Find case IDs falling within duration bounds."""
    if case_summary_df.empty:
        return set()

    mask = (case_summary_df["cycle_time_days"] >= rule.min_days) & (
        case_summary_df["cycle_time_days"] <= rule.max_days
    )
    return set(case_summary_df.loc[mask, "case_id"].dropna().unique())


def evaluate_follower_filter(
    raw_df: pd.DataFrame,
    rule: FollowerFilterRule,
) -> set[str]:
    """Find case IDs where source_activity is followed by target_activity."""
    if raw_df.empty or not rule.source_activity or not rule.target_activity:
        return set()

    # Pre-filter to only events matching either source or target activity
    relevant = raw_df[raw_df["concept:name"].isin([rule.source_activity, rule.target_activity])]
    if relevant.empty:
        return set()

    matching_cases: set[str] = set()

    if rule.follower_type == FollowerType.DIRECTLY_FOLLOWS:
        # Check consecutive rows in raw_df per case
        # Create shifted column for next activity within same case
        sorted_events = raw_df[["case:concept:name", "concept:name"]].copy()
        is_same_case = (
            sorted_events["case:concept:name"] == sorted_events["case:concept:name"].shift(-1)
        )
        is_source = sorted_events["concept:name"] == rule.source_activity
        is_target_next = sorted_events["concept:name"].shift(-1) == rule.target_activity

        direct_matches = sorted_events[is_same_case & is_source & is_target_next]
        matching_cases = set(direct_matches["case:concept:name"].dropna().unique())

    elif rule.follower_type == FollowerType.EVENTUALLY_FOLLOWS:
        # For each case, check if min index of source < max index of target
        grouped = relevant.groupby("case:concept:name", observed=True)
        for case_id, group in grouped:
            source_indices = group.index[group["concept:name"] == rule.source_activity]
            target_indices = group.index[group["concept:name"] == rule.target_activity]
            if not source_indices.empty and not target_indices.empty:
                if source_indices[0] < target_indices[-1]:
                    matching_cases.add(str(case_id))

    return matching_cases


def evaluate_timeframe_filter(
    case_summary_df: pd.DataFrame,
    rule: TimeframeFilterRule,
) -> set[str]:
    """Find case IDs falling within timeframe boundaries."""
    if case_summary_df.empty:
        return set()

    start_bound = (
        pd.to_datetime(rule.start_time_utc, utc=True) if rule.start_time_utc is not None else None
    )
    end_bound = (
        pd.to_datetime(rule.end_time_utc, utc=True) if rule.end_time_utc is not None else None
    )

    starts = pd.to_datetime(case_summary_df["start_time"], utc=True)
    ends = pd.to_datetime(case_summary_df["end_time"], utc=True)

    mask = pd.Series(True, index=case_summary_df.index)

    if rule.timeframe_mode == TimeframeMode.STARTED_IN_TIMEFRAME:
        if start_bound is not None:
            mask &= starts >= start_bound
        if end_bound is not None:
            mask &= starts <= end_bound

    elif rule.timeframe_mode == TimeframeMode.COMPLETED_IN_TIMEFRAME:
        if start_bound is not None:
            mask &= ends >= start_bound
        if end_bound is not None:
            mask &= ends <= end_bound

    elif rule.timeframe_mode == TimeframeMode.ACTIVE_IN_TIMEFRAME:
        # Case is active if ends >= start_bound and starts <= end_bound
        if start_bound is not None:
            mask &= ends >= start_bound
        if end_bound is not None:
            mask &= starts <= end_bound

    return set(case_summary_df.loc[mask, "case_id"].dropna().unique())


def evaluate_rule(
    raw_df: pd.DataFrame,
    case_summary_df: pd.DataFrame,
    rule: BaseFilterRule,
) -> set[str]:
    """Dispatch evaluation to appropriate filter handler."""
    if isinstance(rule, AttributeFilterRule):
        return evaluate_attribute_filter(raw_df, case_summary_df, rule)
    if isinstance(rule, EndpointsFilterRule):
        return evaluate_endpoints_filter(case_summary_df, rule)
    if isinstance(rule, PerformanceFilterRule):
        return evaluate_performance_filter(case_summary_df, rule)
    if isinstance(rule, FollowerFilterRule):
        return evaluate_follower_filter(raw_df, rule)
    if isinstance(rule, TimeframeFilterRule):
        return evaluate_timeframe_filter(case_summary_df, rule)
    return set()


def apply_filter_stack(
    dataset: LoadedDataset,
    rules: list[BaseFilterRule],
) -> tuple[LoadedDataset, list[FilterStepSummary]]:
    """Sequentially apply a list of filter rules to produce a new LoadedDataset."""
    all_case_ids: set[str] = set(dataset.case_summary_df["case_id"].dropna().unique())
    current_case_ids: set[str] = set(all_case_ids)

    summaries: list[FilterStepSummary] = []

    for idx, rule in enumerate(rules, start=1):
        cases_before = len(current_case_ids)

        if not rule.is_enabled:
            retention = (cases_before / len(all_case_ids) * 100.0) if all_case_ids else 0.0
            summaries.append(
                FilterStepSummary(
                    step_index=idx,
                    rule_description=f"[NONAKTIF] {rule.describe()}",
                    is_enabled=False,
                    cases_before=cases_before,
                    cases_after=cases_before,
                    events_after=0,
                    case_retention_pct=retention,
                )
            )
            continue

        # Evaluate rule on current subset
        matching_case_ids = evaluate_rule(dataset.raw_df, dataset.case_summary_df, rule)

        if rule.mode == FilterMode.KEEP_CASES:
            current_case_ids = current_case_ids.intersection(matching_case_ids)
        elif rule.mode == FilterMode.DROP_CASES:
            current_case_ids = current_case_ids.difference(matching_case_ids)

        cases_after = len(current_case_ids)
        retention = (cases_after / len(all_case_ids) * 100.0) if all_case_ids else 0.0

        summaries.append(
            FilterStepSummary(
                step_index=idx,
                rule_description=rule.describe(),
                is_enabled=True,
                cases_before=cases_before,
                cases_after=cases_after,
                events_after=0,  # Will be populated once raw_df is filtered
                case_retention_pct=retention,
            )
        )

    # Build filtered LoadedDataset
    if len(current_case_ids) == len(all_case_ids):
        # No reduction
        filtered_raw = dataset.raw_df
        filtered_summary = dataset.case_summary_df
    else:
        filtered_raw = dataset.raw_df[
            dataset.raw_df["case:concept:name"].isin(current_case_ids)
        ].copy()
        filtered_summary = dataset.case_summary_df[
            dataset.case_summary_df["case_id"].isin(current_case_ids)
        ].copy()

    total_cases = int(len(filtered_summary))
    total_events = int(len(filtered_raw))

    # Update events_after on summaries
    updated_summaries: list[FilterStepSummary] = []
    for s in summaries:
        updated_summaries.append(
            FilterStepSummary(
                step_index=s.step_index,
                rule_description=s.rule_description,
                is_enabled=s.is_enabled,
                cases_before=s.cases_before,
                cases_after=s.cases_after,
                events_after=total_events if s.is_enabled else 0,
                case_retention_pct=s.case_retention_pct,
            )
        )

    activity_freq_df = compute_activity_frequency(filtered_raw, total_cases=total_cases)

    # Overview calculations
    start_time_utc: datetime = (
        filtered_raw["time:timestamp"].min().to_pydatetime()
        if not filtered_raw.empty
        else dataset.overview.start_time_utc
    )
    end_time_utc: datetime = (
        filtered_raw["time:timestamp"].max().to_pydatetime()
        if not filtered_raw.empty
        else dataset.overview.end_time_utc
    )

    mean_ct: float = (
        float(filtered_summary["cycle_time_days"].mean()) if not filtered_summary.empty else 0.0
    )
    median_ct: float = (
        float(filtered_summary["cycle_time_days"].median()) if not filtered_summary.empty else 0.0
    )

    filtered_overview = LogOverview(
        dataset_filename=f"{dataset.overview.dataset_filename} (Filtered: {total_cases:,} cases)",
        total_cases=total_cases,
        total_events=total_events,
        start_time_utc=start_time_utc,
        end_time_utc=end_time_utc,
        mean_cycle_time_days=mean_ct,
        median_cycle_time_days=median_ct,
        detected_attributes=dataset.overview.detected_attributes,
        has_lifecycle=dataset.overview.has_lifecycle,
        has_resource=dataset.overview.has_resource,
        warnings=dataset.overview.warnings,
    )

    filtered_dataset = LoadedDataset(
        file_path=dataset.file_path,
        overview=filtered_overview,
        raw_df=filtered_raw,
        case_summary_df=filtered_summary,
        activity_freq_df=activity_freq_df,
    )

    return filtered_dataset, updated_summaries
