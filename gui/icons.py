"""
SVG icons for the LAN Communication Application.
Contains all media control icons with ON/OFF states.
"""

from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtWidgets import QPushButton

# SVG icon definitions
MICROPHONE_SVG = """
<svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
</svg>
"""

MICROPHONE_OFF_SVG = """
<svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
    <line x1="4" y1="4" x2="20" y2="20" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
</svg>
"""

VIDEO_SVG = """
<svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
</svg>
"""

VIDEO_OFF_SVG = """
<svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/>
    <line x1="4" y1="4" x2="20" y2="20" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
</svg>
"""

SCREEN_SHARE_SVG = """
<svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M20 18c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2H0v2h24v-2h-4zM4 6h16v10H4V6z"/>
    <path d="M9 10l3 3 3-3v6H9v-6z"/>
</svg>
"""

SCREEN_SHARE_OFF_SVG = """
<svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M20 18c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2H0v2h24v-2h-4zM4 6h16v10H4V6z"/>
    <path d="M9 10l3 3 3-3v6H9v-6z"/>
    <line x1="4" y1="4" x2="20" y2="20" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
</svg>
"""

PHONE_HANGUP_SVG = """
<svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 9c-1.6 0-3.15.25-4.6.72v3.1c0 .39-.23.74-.56.9-.98.49-1.87 1.12-2.66 1.85-.18.18-.43.28-.7.28-.28 0-.53-.11-.71-.29L.29 13.08c-.18-.17-.29-.42-.29-.7 0-.28.11-.53.29-.71C3.34 8.78 7.46 7 12 7s8.66 1.78 11.71 4.67c.18.18.29.43.29.71 0 .28-.11.53-.29.7l-2.48 2.48c-.18.18-.43.29-.71.29-.27 0-.52-.1-.7-.28-.79-.73-1.68-1.36-2.66-1.85-.33-.16-.56-.51-.56-.9v-3.1C15.15 9.25 13.6 9 12 9z"/>
</svg>
"""

USERS_SVG = """
<svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M16 4c0-1.11.89-2 2-2s2 .89 2 2-.89 2-2 2-2-.89-2-2zm4 18v-6h2.5l-2.54-7.63A1.5 1.5 0 0 0 18.54 8H17.5c-.8 0-1.54.37-2.01 1.01L14 12l-1.49-2.99A2.5 2.5 0 0 0 10.26 8H9.74c-.8 0-1.54.37-2.01 1.01L6.24 12H9v10h2v-6h2v6h2zm-7.5 0v-7.5L11 12l-1.5 2.5V22H8zm-6.5 0v-4.5L4.5 15 3 17.5V22H1z"/>
</svg>
"""

CHAT_SVG = """
<svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h4v3c0 .6.4 1 1 1 .2 0 .5-.1.7-.3L14.4 18H20c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-7 13H7v-2h6v2zm3-4H7V9h9v2zm0-4H7V5h9v2z"/>
</svg>
"""

def create_svg_icon(svg_content: str, size: QSize = QSize(24, 24), color: str = "white") -> QIcon:
    """
    Create a QIcon from SVG content with specified color.
    
    Args:
        svg_content: SVG content as string
        size: Icon size
        color: Icon color
    
    Returns:
        QIcon object
    """
    # Replace currentColor with the specified color
    colored_svg = svg_content.replace("currentColor", color)
    
    # Create QSvgRenderer
    svg_bytes = QByteArray(colored_svg.encode('utf-8'))
    renderer = QSvgRenderer(svg_bytes)
    
    # Create pixmap
    pixmap = QPixmap(size)
    pixmap.fill(Qt.transparent)
    
    # Render SVG to pixmap
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    
    return QIcon(pixmap)

def create_icon_with_slash(svg_content: str, size: QSize = QSize(24, 24), color: str = "white") -> QIcon:
    """
    Create a QIcon from SVG content with a diagonal slash overlay.
    
    Args:
        svg_content: SVG content as string
        size: Icon size
        color: Icon color
    
    Returns:
        QIcon object with slash overlay
    """
    # Replace currentColor with the specified color
    colored_svg = svg_content.replace("currentColor", color)
    
    # Add slash line to SVG
    svg_with_slash = colored_svg.replace(
        "</svg>", 
        f'<line x1="3" y1="3" x2="21" y2="21" stroke="{color}" stroke-width="2"/></svg>'
    )
    
    # Create QSvgRenderer
    svg_bytes = QByteArray(svg_with_slash.encode('utf-8'))
    renderer = QSvgRenderer(svg_bytes)
    
    # Create pixmap
    pixmap = QPixmap(size)
    pixmap.fill(Qt.transparent)
    
    # Render SVG to pixmap
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    
    return QIcon(pixmap)

def set_button_icon(button: QPushButton, svg_content: str, is_active: bool, size: QSize = QSize(24, 24)):
    """
    Set button icon based on active state.
    
    Args:
        button: QPushButton to update
        svg_content: SVG content for the icon
        is_active: Whether the feature is active
        size: Icon size
    """
    if is_active:
        # Active state - white icon on grey background
        icon = create_svg_icon(svg_content, size, "white")
        button.setIcon(icon)
        button.setText("")
        button.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border: none;
                border-radius: 25px;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
    else:
        # Inactive state - white icon with slash on red background
        icon = create_icon_with_slash(svg_content, size, "white")
        button.setIcon(icon)
        button.setText("")
        button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                border: none;
                border-radius: 25px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)