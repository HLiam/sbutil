import time
import objc_util
from functools import wraps
from threading import Thread


_app = objc_util.ObjCClass('UIApplication').sharedApplication()
_status_bar = _app.statusBar()
_color = objc_util.ObjCClass('UIColor')


def _run_in_background(func):
    """Run func in a new thread. The thread is expected to exit on its own."""
    @wraps(func)
    def wrapped(*args, **kwargs):
        Thread(target=func, args=args, kwargs=kwargs).start()
    return wrapped


class Glyph:
    """This class contains all glyphs that can be added to the status bar by
    default.
    
    Attributes:
        NIGHT_MODE
        AIRPLANE_MODE
        CELLULAR_BARS
        TEXT
        WIFI_BARS
        TIME_RIGHT
        BATTERY_PERCENT
        BLUETOOTH_BATTERY
        PHONE
        CLOCK
        SLANTED_PLUS
        LOCATION
        ROTATION_LOCK
        AIRPLAY
        MICROPHONE
        DESK
        VPN
        HANGUP
        ACTIVITY_SPINNER
        LOCK
        WATER_INDICATOR
        BLUETOOTH_HEADPHONES
    """
    # Im probably missing a few (some useless ones are removed,
    # mostly everything past 33).
    NIGHT_MODE = 1
    AIRPLANE_MODE = 2
    CELLULAR_BARS = 3
    TEXT = 4
    WIFI_BARS = 6
    TIME_RIGHT = 7
    BATTERY_PERCENT = 10
    BLUETOOTH_BATTERY = 11
    PHONE = 13
    CLOCK = 14
    PLUS = 15  # ?
    LOCATION = 17
    ROTATION_LOCK = 18
    AIRPLAY = 20
    MICROPHONE = 21
    DESK = 23
    VPN = 24
    HANGUP = 25  # ?
    ACTIVITY_SPINNER = 26
    LOCK = 31  # shows animation when removed.
    WATER_INDICATOR = 32
    BLUETOOTH_HEADPHONES = 33


class _GlyphSet:
    """Glyph manager. Can be used as a context manager by calling it."""
    def __init__(self, _items=None):
        self._context_glyphs = []
        if _items is None:
            _items = {}
        self._items = set(_items)
        for glyph in self._items:
            self.add(glyph)
    
    def __repr__(self):
        return f'_GlyphList(_items={repr(self._items)})'
    
    def __contains__(self, glyph):
        return glyph in self._items
    
    def __iadd__(self, glyph):
        self._items |= glyph
        self._add_glyph(glyph)
    
    def __iter__(self):
        return iter(self._items)
    
    def __call__(self, *args):
        """For use as as a context manager."""
        self._context_glyphs.append(args)
        return self
    
    def __enter__(self):
        for glyph in self._context_glyphs[-1]:
            self.add(glyph)
    
    def __exit__(self, exc_type, exc_value, traceback):
        for glyph in self._context_glyphs[-1]:
            self.remove(glyph)
        del self._context_glyphs[-1]
    
    def _add_glyph(self, glyph):
        _app.addStatusBarItem_(glyph)
    
    def _remove_glyph(self, glyph):
        _app.removeStatusBarItem_(glyph)
    
    def add(self, glyph):
        """Add a glyph to the status bar."""
        self._items.add(glyph)
        self._add_glyph(glyph)
    
    def remove(self, glyph):
        """Remove a glyph from the status bar and from the set.
        
        If the glyph is not in the set, try to remove it before the error occurs.
        """
        self._remove_glyph(glyph)
        self._items.remove(glyph)
    
    def clear(self):
        """Remove all glyphs in the status bar and clear the set."""
        for glyph in self._items:
            self._remove_glyph(glyph)
        self._items.clear()


class StatusBar:
    """A class for manipulating the status bar. Uses a borg pattern."""
    _shared_state = {}
    
    def __init__(self):
        if self._shared_state:
            self.__dict__ = StatusBar._shared_state
        else:
            StatusBar._shared_state = self.__dict__
            self._active_glyphs = _GlyphSet()
            self._glyph_container_view = _status_bar.subviews()[1]
    
    @property
    def alpha(self):
        """The status bar's alpha."""
        return _status_bar.alpha()
    
    @alpha.setter
    def alpha(self, value):
        _status_bar.setAlpha_(value)
    
    @property
    def width(self):
        return _status_bar.currentWidth()
    
    @property
    def height(self):
        """The status bar's height.'"""
        return _status_bar.currentHeight()
    
    @property
    def foreground_color(self):
        """The foreground color of the status bar. None is defaul.
        
        Should be a `Color` object.
        """
        return _status_bar.foregroundColor()
    
    @foreground_color.setter
    def foreground_color(self, color):
        _status_bar.setForegroundColor_(create_color(color))
    
    @property
    def background_color(self):
        """The background color of the status bar. None is default.
        
        Should be a `Color` object.
        """
        return _status_bar.backgroundColor()
    
    @background_color.setter
    def background_color(self, color):
        _status_bar.setBackgroundColor_(create_color(color))
    
    @property
    def style(self):
        """The style of the status bar. Can be one of 'success' (green) or
        'error' (red).
        
        `None` removes the style.
        """
        style_map = {1: 'success', 2: 'error', 0: None}
        return style_map[_status_bar.styleOverrides()]
    
    @style.setter
    def style(self, style):
        style_map = {'success': 1, 'error': 2, None: 0}
        _app.removeStatusBarStyleOverrides_(style_map[self.style])
        if style is None:
            return
        if style == 'success':
            style = 1
        elif style == 'error':
            style = 2
        else:
            raise ValueError(f"style must be 'success' or 'error', not {repr(style)}")
        _app.addStatusBarStyleOverrides_(style)
    
    @property
    def glyphs(self):
        """A set of glyphs that are currently displayed on the status bar.

        This is directly responsible for adding and remove items. This can
        also be called to use it as a context manager by passing the glyphs
        to be displayed for the duration of the context manager.

        Examples:
            To add and remove the airplane mode glyph to the status bar:
            >>> from sbutil import StatusBar, Glyph
            >>> sb = StatusBar()
            >>> sb.glyphs.add(Glyph.AIRPLANE_MODE)
            >>> # Then to remove it:
            >>> sb.glyphs.remove(Glyph.AIRPLANE_MODE)
            
            The `clear` method can also be used to remove all glyphs:
            >>> from sbutil import StatusBar, Glyph
            >>> sb = StatusBar()
            >>> sb.glyphs.add(Glyph.AIRPLANE_MODE)
            >>> sb.glyphs.add(Glyph.NIGHT_MODE)
            >>> sb.glyphs.clear()  # Remove both glyphs
            
            To use it as a context manager:
            >>> sb = StatusBar()
            >>> with sb.glyphs(Glyph.AIRPLANE_MODE, Glyph.NIGHT_MODE):
            ...     # do something with the airplane mode and night mode glyphs shown
            ...     pass  
        
        """
        return self._active_glyphs
    
    @glyphs.setter
    def glyphs(self, other):
        self._active_glyphs.clear()
        self._active_glyphs = _GlyphSet(other)
    
    def show(self, fade_duration=0):
        """Fade the status bar in.
        
        Args:
            fade_duration(int, float, optional): The time that the fade in
                animation will take in seconds. Defaults to 0.
        """
        _status_bar.setHidden_animated_(False, fade_duration)
    
    def hide(self, fade_duration=0):
        """Fade the status bar out.
        
        Args:
            fade_duration(int, float, optional): The time that the fade out
                animation will take in seconds. Defaults to 0.
        """
        _status_bar.setHidden_animated_(True, fade_duration)
    
    @_run_in_background
    def flash_style(self, style, duration=1.5):
        """Flash the status bar as a style for set duration.
        
        Args:
            style(str): The color to flash. Can be one of 'success' or 'error'.
            duration(int, float): The duration (in seconds) to flash the color
            for.
        """
        try:
            self.style = style
            time.sleep(duration)
        finally:
            self.style = None


def create_color(c):
    if c is None:
        return None
    else:
        if len(c) == 3:
            c += (1,)
    return _color.akColorWithSRGBRed_green_blue_alpha_(*c)


if __name__ == '__main__':
    sb = StatusBar()
