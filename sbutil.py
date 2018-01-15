import time
import objc_util
from functools import wraps
from threading import Thread


_app = objc_util.ObjCClass('UIApplication').sharedApplication()
_status_bar = _app.statusBar()
_color = objc_util.ObjCClass('UICachedDeviceRGBColor')


def _run_in_background(func):
    """Run func in a new thread. The thread is expected to exit on its own."""
    @wraps(func)
    def wrapped(*args, **kwargs):
        Thread(target=func, args=args, kwargs=kwargs).start()
    return wrapped


class _Color:
    """Intantiates RGB (0-1) colors. All colors use this."""
    def __new__(cls, c):
        if c is None:
            return None
        else:
            if len(c) == 3:
                c += (1,)
            r, g, b, a = c
            r, g, b = r*255, g*255, b*255
        return _color.colorWithRed_green_blue_alpha_(r, g, b, a)


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
    SLANTED_PLUS = 15  # ?
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
    def __init__(self, _items=None):
        if _items is None:
            _items = {}
        self._items = set(_items)
    
    def __repr__(self):
        return f'_GlyphList(_items={repr(self._items)})'
    
    def __contains__(self, glyph):
        return glyph in self._items
    
    def __iadd__(self, glyph):
        self._items |= glyph
        self._add_glyph(glyph)
    
    def __iter__(self):
        return iter(self._items)
    
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
        _status_bar.alpha()
    
    @alpha.setter
    def alpha(self, value):
        _status_bar.setAlpha_(value)
    
    @property
    def width(self):
        return _status_bar.currentHeight()
    
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
        _status_bar.setForegroundColor_(_Color(color))
    
    @property
    def background_color(self):
        """The background color of the status bar. None is default.
        
        Should be a `Color` object.
        """
        return _status_bar.backgroundColor()
    
    @background_color.setter
    def background_color(self, color):
        _status_bar.setBackgroundColor_(_Color(color))
    
    @property
    def style(self):
        """The style of the status bar. Can be one of 'success' (green) or
        'error' (red).
        
        `None` remove the style.
        """
        return _status_bar.styleOverrides()
    
    @style.setter
    def style(self, style):
        _app.removeStatusBarStyleOverrides_(self.style)
        if style is None:
            return
        if style == 'success':
            style = 1
        elif style == 'error':
            style = 2
        else:
            raise ValueError(f"style must be 'success' or 'error', not {repr(style)}")
        _app.addStatusBarStyleOverrides_(style)
    
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
    
    @property
    def glyphs(self):
        """A set of glyphs that are currently displayed on the status bar.
        
        This is directly responsible for adding and remove items.
        
        Examples:
            To add and remove the airplane mode glyph to the status bar:
            >>> sb = StatusBar()
            >>> sb.glyphs.add(Glyph.AIRPLANE_MODE)
            >>> # Then to remove it:
            >>> sb.glyphs.remove(Glyph.AIRPLANE_MODE)
            
            The `clear` method can also be used to remove all glyphs:
            >>> sb = StatusBar()
            >>> sb.glyphs.add(Glyph.AIRPLANE_MODE)
            >>> sb.glyphs.add(Glyph.NIGHT_MODE)
            >>> sb.glyphs.clear()  #Remove both glyphs.
        """
        return self._active_glyphs
    
    @glyphs.setter
    def glyphs(self, other):
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
