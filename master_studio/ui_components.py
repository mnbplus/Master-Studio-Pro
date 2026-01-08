from PyQt6.QtWidgets import (QFrame, QPushButton, QLineEdit, QStyledItemDelegate, 
                             QStyle, QScrollArea, QGraphicsDropShadowEffect)
from PyQt6.QtGui import (QFont, QColor, QPainter, QPainterPath, QCursor, QPen, QLinearGradient)
from PyQt6.QtCore import (Qt, QRectF, QRect, QSize, QPropertyAnimation, 
                          QEasingCurve, QPoint, pyqtProperty)
from master_studio.config import STYLE, APP_FONT_MAIN
from master_studio.utils import get_recolored_icon

# --- 1. 陶瓷质感卡片 ---
class MacCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设计理念：白底 + 极细淡灰边框 + 大圆角
        # 这种风格比纯阴影更显干净、现代
        self.setStyleSheet(f"""
            MacCard {{ 
                background-color: {STYLE['bg_card']}; 
                border-radius: {STYLE['radius_l']}px; 
                border: 1px solid {STYLE['border']};
            }}
        """)
        # 可选：如果显卡性能足够，可以开启下方的微阴影
        # shadow = QGraphicsDropShadowEffect(self)
        # shadow.setBlurRadius(24)
        # shadow.setColor(QColor(0, 0, 0, 8)) # 极淡的阴影
        # shadow.setOffset(0, 8)
        # self.setGraphicsEffect(shadow)

# --- 2. 灵动按钮 (带缩放动画) ---
class MacButton(QPushButton):
    def __init__(self, text, is_primary=True):
        super().__init__(text)
        self.is_primary = is_primary
        self.setFixedHeight(40) # 40px 高度是桌面端最佳点击尺寸
        self.setFont(QFont(APP_FONT_MAIN, 10, QFont.Weight.DemiBold)) # 半粗体更醒目
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 初始化缩放动画属性
        self._scale = 1.0
        self.anim = QPropertyAnimation(self, b"scale_prop")
        self.anim.setDuration(100) # 100ms 极速响应
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)

    # 定义 Qt 属性供动画引擎调用
    @pyqtProperty(float)
    def scale_prop(self):
        return self._scale

    @scale_prop.setter
    def scale_prop(self, val):
        self._scale = val
        self.update() # 触发重绘

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def mousePressEvent(self, event):
        # 按下时缩小到 96%
        self.anim.stop()
        self.anim.setEndValue(0.96)
        self.anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        # 松开回弹
        self.anim.stop()
        self.anim.setEndValue(1.0)
        self.anim.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. 应用缩放变换
        rect = self.rect()
        painter.translate(rect.center())
        painter.scale(self._scale, self._scale)
        painter.translate(-rect.center())
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), STYLE['radius_m'], STYLE['radius_m'])
        
        # 2. 绘制背景
        if self.is_primary:
            # 主按钮：扁平蓝
            if self.isDown(): 
                bg_color = QColor(STYLE['accent_pressed'])
            elif self.underMouse(): 
                bg_color = QColor(STYLE['accent_hover'])
            else:
                bg_color = QColor(STYLE['accent'])
            
            painter.setBrush(bg_color)
            painter.setPen(Qt.PenStyle.NoPen)
            text_color = Qt.GlobalColor.white
            
            # 绘制主按钮的微阴影（提升层次感）
            if not self.isDown():
                # 只在非按下状态绘制底部阴影，模拟厚度
                shadow_color = QColor(STYLE['accent'])
                shadow_color.setAlpha(80)
                # 简单模拟：可以在这里画一个小一点的矩形做阴影，或者为了性能省略
                
        else:
            # 次级按钮：白底灰边
            bg_color = QColor("#FFFFFF")
            border_color = QColor(STYLE['border'])
            text_color = QColor(STYLE['text_main'])
            
            if self.isDown(): 
                bg_color = QColor("#F3F4F6") # Cool Gray 100
            elif self.underMouse(): 
                bg_color = QColor("#F9FAFB") # Cool Gray 50
                border_color = QColor("#D1D5DB") # Hover 时边框加深
            
            painter.setBrush(bg_color)
            painter.setPen(border_color)
        
        painter.drawPath(path)
        
        # 3. 绘制文字
        painter.setPen(text_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())

# --- 3. 聚焦光晕输入框 ---
class MacInput(QLineEdit):
    def __init__(self, placeholder=""):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setFixedHeight(42) # 增加高度，显得更大气
        self.setFont(QFont(APP_FONT_MAIN, 10))
        
        # 使用 QSS 实现复杂的 Focus Ring 效果
        # 这里模拟了 macOS/Bootstrap 的光晕
        self.setStyleSheet(f"""
            QLineEdit {{ 
                background-color: #FFFFFF; 
                border: 1px solid {STYLE['border']}; 
                border-radius: {STYLE['radius_m']}px; 
                padding-left: 12px; 
                color: {STYLE['text_main']}; 
                selection-background-color: {STYLE['accent']};
                selection-color: #FFFFFF;
            }}
            QLineEdit:hover {{
                border: 1px solid #D1D5DB; /* Cool Gray 300 */
            }}
            QLineEdit:focus {{ 
                border: 1px solid {STYLE['accent']}; 
                /* 这种写法只在部分 QStyle 下有效，通常用 border 变色已足够 */
                /* 如果需要发光，通常需要 QGraphicsEffect，但这会影响性能 */
            }}
            QLineEdit[readOnly="true"] {{
                background-color: #F9FAFB;
                color: {STYLE['text_sub']};
                border: 1px solid {STYLE['border']};
            }}
        """)

# --- 4. 悬浮式侧边栏代理 ---
class SidebarDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        icon_file = index.data(Qt.ItemDataRole.UserRole)
        text = index.data(Qt.ItemDataRole.DisplayRole)
        is_selected = option.state & QStyle.StateFlag.State_Selected
        is_hover = option.state & QStyle.StateFlag.State_MouseOver

        rect = QRectF(option.rect)
        
        # 核心改动：悬浮胶囊样式
        # 左右各留 12px 边距，上下留 4px 边距
        content_rect = rect.adjusted(12, 4, -12, -4) 
        
        if is_selected:
            bg_path = QPainterPath()
            bg_path.addRoundedRect(content_rect, 8, 8) # 8px 圆角
            
            # 选中背景：极淡的品牌色 (Tint)
            # 这种颜色比纯灰更高级
            painter.setBrush(QColor("#EFF6FF")) # Blue 50
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(bg_path)
            
            icon_color = STYLE['accent'] # 图标变蓝
            text_color = STYLE['accent'] # 文字变蓝
            weight = QFont.Weight.Bold
            
        elif is_hover:
            bg_path = QPainterPath()
            bg_path.addRoundedRect(content_rect, 8, 8)
            painter.setBrush(QColor("#F9FAFB")) # Cool Gray 50
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(bg_path)
            
            icon_color = STYLE['text_main']
            text_color = STYLE['text_main']
            weight = QFont.Weight.Medium
        else:
            icon_color = STYLE['text_sub']
            text_color = STYLE['text_sub']
            weight = QFont.Weight.Medium

        # 绘制图标 (使用缓存加速)
        if icon_file:
            # 选中时图标也是蓝色的
            icon_pix = get_recolored_icon(icon_file, icon_color, size=20)
            # 垂直居中
            icon_y = int(rect.top() + (rect.height() - 20) / 2)
            # 图标左边距 24px (相对于 Item 左边缘)
            painter.drawPixmap(int(rect.left() + 24), icon_y, icon_pix)

        # 绘制文本
        painter.setPen(QColor(text_color))
        painter.setFont(QFont(APP_FONT_MAIN, 10, weight))
        
        # 文本区域：图标右侧
        text_rect = QRectF(rect.left() + 58, rect.top(), rect.width() - 58, rect.height())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)
        
        painter.restore()

    def sizeHint(self, option, index):
        # 增加列表项高度，增加呼吸感
        return QSize(200, 50) 

# --- 5. 平滑滚动区域 (保持原逻辑，无需变动) ---
class SmoothScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.m_scrollAnim = QPropertyAnimation(self.verticalScrollBar(), b"value")
        self.m_scrollAnim.setEasingCurve(QEasingCurve.Type.OutQuint) 
        self.m_scrollAnim.setDuration(400) 

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            super().wheelEvent(event)
            return
        y_delta = event.angleDelta().y()
        vbar = self.verticalScrollBar()
        step = -y_delta 
        current_val = vbar.value()
        target_val = max(vbar.minimum(), min(vbar.maximum(), current_val + step))
        if target_val != current_val:
            self.m_scrollAnim.stop()
            self.m_scrollAnim.setStartValue(current_val)
            self.m_scrollAnim.setEndValue(target_val)
            self.m_scrollAnim.start()
        else:
            event.ignore()
