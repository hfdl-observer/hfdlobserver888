# cul.py
# copyright 2024 Kuupa Ork <kuupaork+github@hfdl.observer>
# see LICENSE (or https://github.com/hfdl-observer/hfdlobserver888/blob/main/LICENSE) for terms of use.
# TL;DR: BSD 3-clause
#

import asyncio
import collections
import functools
import datetime
import logging
import math

from typing import Any, Callable, Optional

import rich.console
import rich.highlighter
import rich.layout
import rich.live
import rich.logging
import rich.markdown
import rich.style
import rich.table
import rich.text

import hfdl_observer.hfdl

import main
import packet_stats

logger = logging.getLogger(__name__)
start = datetime.datetime.now()
SCREEN_REFRESH_RATE = 2


class ObserverDisplay:
    status: Optional[rich.table.Table] = None
    counts: Optional[rich.table.Table] = None
    tty_bar: Optional[rich.table.Table] = None
    tty: Optional[rich.table.Table] = None
    forecast: Optional[rich.table.Text] = None

    def __init__(
        self, console: rich.console.Console, ticker: 'Ticker', forecaster: hfdl_observer.bus.RemoteURLRefresher
    ) -> None:
        self.console = console
        self.ticker = ticker
        self.root = rich.layout.Layout("HFDL.observer/888")
        self.ticker.display = self
        self.update_status()
        self.update_tty_bar()
        forecaster.subscribe('response', self.on_forecast)

    def update(self) -> None:
        t = rich.table.Table.grid(expand=True, pad_edge=False, padding=(0, 0))
        if self.status:
            t.add_row(self.status)
        if self.counts:
            t.add_row(self.counts)
        if self.tty_bar:
            t.add_row(self.tty_bar)
        if self.tty:
            t.add_row(self.tty)
        if t.row_count:
            self.root.update(t)

    def update_status(self) -> None:
        table = rich.table.Table.grid(expand=True)
        table.add_column()
        table.add_column(justify="center")
        table.add_column(justify="right")
        text = rich.text.Text()
        text.append(' 📡 ')
        text.append('HFDL.observer/888', style='bold')
        text.append(' - ')
        text.append('A multi-headed dumphfdl receiver for Web-888 devices', style='yellow')

        uptime = datetime.datetime.now() - start
        uptime -= datetime.timedelta(0, 0, uptime.microseconds)
        right = rich.text.Text(f'UP {uptime}')

        table.add_row(text, self.forecast or '', right, style='on dark_green')
        self.status = table
        # self.update()

    def update_tty_bar(self) -> None:
        table = rich.table.Table.grid(expand=True)
        table.add_row(' 📰 Log', style='bright_white on white')
        self.tty_bar = table

    def update_log(self, ring: collections.deque) -> None:
        # WARNING: do not log from within this method.
        table = rich.table.Table.grid(expand=True)
        available_space = (
            self.current_height
            - (self.counts.row_count if self.counts else 0)
            - (self.status.row_count if self.status else 0)
            - (self.tty_bar.row_count if self.tty_bar else 0)
            - 1  # trailing blank
        )
        entries = list(ring)[-available_space:]
        for row in entries:
            table.add_row(row)
        self.tty = table

    def update_counts(self, table: rich.table.Table) -> None:
        if table.row_count:
            self.counts = table
        # self.update()

    def on_forecast(self, data: Any) -> None:
        try:
            styles = {
                "extreme": "yellow1 on dark_red",
                "severe": "black on red1",
                "strong": "black on dark_orange",
                "moderate": "black on orange1",
                "minor": "black on gold1",
                "none": "white on bright_black"
            }
            # value_map = {
            #     "0": "∘",
            #     "1": "▁",
            #     "2": "▃",
            #     "3": "▅",
            #     "4": "▆",
            #     "5": "▓",
            # }
            recent = data['-1']
            current = data['0']
            forecast1d = data['1']
            # forecast2d = data['2']
            # forecast3d = data['3']
            text = rich.text.Text()
            text.append(f'R{recent["R"]["Scale"]}', style=styles[recent["R"]["Text"]])
            text.append('|')
            text.append(f'S{recent["S"]["Scale"]}', style=styles[recent["S"]["Text"]])
            text.append('|')
            text.append(f'G{recent["G"]["Scale"]}', style=styles[recent["G"]["Text"]])
            text.append('  ')
            text.append(f'R{current["R"]["Scale"]}', style=styles[current["R"]["Text"]])
            text.append('|')
            text.append(f'S{current["S"]["Scale"]}', style=styles[current["S"]["Text"]])
            text.append('|')
            text.append(f'G{current["G"]["Scale"]}', style=styles[current["G"]["Text"]])
            text.append('  ')
            text.append(f'R{forecast1d["R"]["MinorProb"]}/{forecast1d["R"]["MajorProb"]}', styles["none"]),
            text.append('|')
            text.append(f'S{forecast1d["S"]["Prob"]}', styles["none"]),
            text.append('|')
            text.append(f'G{forecast1d["G"]["Scale"]}', styles[forecast1d["G"]["Text"]]),
            self.forecast = text
        except Exception as err:
            logger.warning('ignoring forecaster error', exc_info=err)

    @property
    def current_width(self) -> int:
        return self.console.options.size.width

    @property
    def current_height(self) -> int:
        return self.console.options.size.height or 25


BASE_HEADERS = ['NOW'] + (['   '] * 4 + [' ¦ '] + ['   '] * 4 + [' ┇ ']) * 12
COUNT_HEADER = rich.style.Style.parse('bright_white on white')
SUBDUED_TEXT = rich.style.Style.parse('bright_black on black')
NORMAL_TEXT = rich.style.Style.parse('white on black')
PROMINENT_TEXT = rich.style.Style.parse('bright_white on black')


class Ticker(packet_stats.PacketCounter):
    last_render_time: float = 0
    display: ObserverDisplay

    def register(self, observer: main.Observer888) -> None:
        observer.subscribe('packet', self.on_hfdl)
        observer.subscribe('observing', self.on_observing)
        observer.subscribe('frequencies', self.on_frequencies)

    def on_hfdl(self, packet: hfdl_observer.hfdl.HFDLPacketInfo) -> None:
        if not self.task:
            self.start()
        super().on_hfdl(packet)
        self.maybe_render()

    def on_observing(self, active_frequencies: list[int]) -> None:
        if not self.task:
            self.start()
        super().on_observing(active_frequencies)

    @functools.cache
    def style(self, value: int) -> Optional[rich.style.Style]:
        # with 13 slots per 32 seconds, we should not see any more than 25 packets per minute on any given frequency
        if value:
            rgb = spectrum_colour(value, 25)
            return rich.style.Style.parse(f'black on rgb({",".join(str(i) for i in rgb)})')
        return None

    def maybe_render(self) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        if now - self.last_render_time > SCREEN_REFRESH_RATE / 2.0:
            self.render()

    def render(self) -> None:
        table = rich.table.Table(
            show_header=False, show_footer=False, show_edge=False, show_lines=False, expand=True
        )
        if self.samples:
            width = self.display.current_width - (3 + 9 + 6 + 4 + 1) - 3
            possible_bins = width // 3
            binned_samples = self.bins(-1 * 60 * possible_bins, 60)
            headers, rows = self.sample_counts(binned_samples)
            decorated_table = self.decorated_counts_table(headers, rows)

            table = rich.table.Table.grid(expand=True)
            display_headers = BASE_HEADERS[:len(headers)]

            table.add_row(f" 📊 Packets/min   {''.join(display_headers)}", style=COUNT_HEADER)
            for freq, data in decorated_table.items():
                row_text = rich.text.Text(style=SUBDUED_TEXT)
                row_text.append(f'{data["active"]: ^3}', style=PROMINENT_TEXT)
                station = self.observed_stations[freq]
                sname = packet_stats.STATION_ABBREVIATIONS.get(station['id'], '')
                if station.get('pending'):
                    row_text.append(f'{sname.lower(): >9}', style='grey30')
                else:
                    row_text.append(f'{sname: >9}', style='grey66')
                row_text.append(f'{freq: >6}', style=NORMAL_TEXT)
                bins: list[str] = data["symbols"]  # type: ignore  # shut up, mypy
                counts: list[int] = data["counts"]  # type: ignore  # shut up, mypy
                for colno, (cnt, bn) in enumerate(zip(counts, bins)):
                    cell = f'{bn: ^3}' if (cnt > 0 or colno == 0 or colno % 5 != 0) else display_headers[colno]
                    row_text.append(cell, style=self.style(cnt))
                tot = data["total"]
                if tot:
                    row_text.append(f'{tot: >4}', style=NORMAL_TEXT)
                table.add_row(row_text)
            self.display.update_counts(table)
            self.last_render_time = datetime.datetime.now(datetime.timezone.utc).timestamp()
        else:
            table.add_row(" 📊 Packets/min", style=COUNT_HEADER)
            table.add_row("Awaiting data...")
        self.display.update_counts(table)


def hsv_rgb(hue: float, saturation: float, value: float) -> tuple[float, float, float]:
    i = math.floor(hue * 6)
    f = hue * 6 - i
    p = value * (1 - saturation)
    q = value * (1 - f * saturation)
    t = value * (1 - (1 - f) * saturation)
    r, g, b = [
        (value, t, p),
        (q, value, p),
        (p, value, t),
        (p, q, value),
        (t, p, value),
        (value, p, q),
    ][int(i % 6)]
    return r, g, b


def spectrum_colour(value: int, max_value: int) -> tuple[int, int, int]:
    effective = max_value - min(max(0, value), max_value)
    start_hue = 280
    hue_range = 300
    hue = (start_hue + hue_range * effective / max_value) % 360
    hsv = hsv_rgb(hue / 360, 1, 1)
    return (int(hsv[0] * 255), int(hsv[1] * 255), int(hsv[2] * 255))


class ConsoleRedirector(rich.console.Console):
    ring: collections.deque
    output: Optional[Callable[[collections.deque], None]] = None

    def print(self, something: Any) -> None:  # type: ignore   # shut up, mypy.
        self.ring.append(something)
        if self.output is not None:
            self.output(self.ring)
        else:
            super().print(something)

    def ensure_size(self, size: int) -> None:
        if self.ring.maxlen and size > self.ring.maxlen:
            self.ring = collections.deque(self.ring, size)

    @classmethod
    def create(cls, size: int) -> 'ConsoleRedirector':
        that = cls()
        that.ring = collections.deque(maxlen=size)
        return that


class RichLive(rich.live.Live):
    on_refresh: Optional[list[Callable]] = None

    def refresh(self) -> None:
        for callback in self.on_refresh or []:
            callback()
        super().refresh()


def screen(loghandler: Optional[logging.Handler], debug: bool = True) -> None:
    console = rich.console.Console()
    console.clear()
    logging_console = ConsoleRedirector.create(max(console.options.size.height or 50, 50))
    logging_handler = rich.logging.RichHandler(
        console=logging_console,
        show_time=True,
        highlighter=rich.highlighter.NullHighlighter(),
        enable_link_path=False,
    )
    ticker = Ticker()
    ticker.refresh_period = 60

    forecaster = hfdl_observer.bus.RemoteURLRefresher('https://services.swpc.noaa.gov/products/noaa-scales.json', 617)

    display = ObserverDisplay(console, ticker, forecaster)

    # setup logging
    logging_console.output = display.update_log
    FORMAT = "%(message)s"
    handlers: list[logging.Handler] = [logging_handler]
    if loghandler:
        handlers.append(loghandler)
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format=FORMAT,
        datefmt="[%X]",
        handlers=handlers,
        force=True
    )

    def observing(observer: main.Observer888) -> None:
        ticker.register(observer)
        asyncio.get_event_loop().create_task(forecaster.run())

    with RichLive(
        display.root, refresh_per_second=SCREEN_REFRESH_RATE, console=console, transient=True, screen=True,
        redirect_stderr=False, redirect_stdout=False, vertical_overflow="crop",
    ) as live:
        live.on_refresh = [  # type: ignore[attr-defined]
            display.update_status,
            display.update,
        ]
        main.observe(on_observer=observing)


if __name__ == '__main__':
    screen(None)
