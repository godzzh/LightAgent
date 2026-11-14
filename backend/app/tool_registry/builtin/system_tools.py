"""内置工具：时间与日期。"""
from __future__ import annotations

from datetime import datetime, timedelta

from app.tool_registry.registry import BaseTool, ToolSpec, register


class CurrentTimeTool(BaseTool):
    spec = ToolSpec(
        name="current_time",
        description="获取当前日期和时间。可指定 IANA 时区（如 Asia/Shanghai），默认本机时区。",
        parameters=[
            {
                "name": "timezone",
                "type": "string",
                "description": "IANA 时区名，例如 Asia/Shanghai、UTC",
                "required": False,
                "default": "Asia/Shanghai",
            }
        ],
    )

    async def execute(self, args: dict) -> dict:
        tz_name = args.get("timezone") or "Asia/Shanghai"
        try:
            from zoneinfo import ZoneInfo

            now = datetime.now(ZoneInfo(tz_name))
        except Exception:
            now = datetime.now()
            tz_name = "local"
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return {
            "iso": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "weekday": weekdays[now.weekday()],
            "timezone": tz_name,
            "timestamp": int(now.timestamp()),
        }


class DateCalcTool(BaseTool):
    spec = ToolSpec(
        name="date_calc",
        description="日期计算：给定基准日期与偏移天数，返回计算后的日期；也可计算两个日期相差天数。",
        parameters=[
            {"name": "base_date", "type": "string", "description": "基准日期 YYYY-MM-DD，默认今天", "required": False},
            {"name": "days", "type": "integer", "description": "偏移天数，可为负数", "required": False, "default": 0},
            {"name": "target_date", "type": "string", "description": "可选，计算与基准日期的相差天数", "required": False},
        ],
    )

    async def execute(self, args: dict) -> dict:
        base = (
            datetime.strptime(args["base_date"], "%Y-%m-%d").date()
            if args.get("base_date")
            else datetime.now().date()
        )
        result: dict = {"base_date": base.isoformat()}
        if args.get("target_date"):
            target = datetime.strptime(args["target_date"], "%Y-%m-%d").date()
            result["target_date"] = target.isoformat()
            result["diff_days"] = (target - base).days
        days = int(args.get("days") or 0)
        shifted = base + timedelta(days=days)
        result["offset_days"] = days
        result["result_date"] = shifted.isoformat()
        result["result_weekday"] = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][shifted.weekday()]
        return result


register(CurrentTimeTool())
register(DateCalcTool())
