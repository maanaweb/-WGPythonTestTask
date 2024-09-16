import random

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsItem, QGraphicsLineItem)
from PyQt6.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt6.QtGui import QColor, QBrush, QPen


class RectItem(QGraphicsRectItem):
    WIDTH = 100
    HEIGHT = 50

    def __init__(self):
        super().__init__()

        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        brush = QBrush(QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        self.setBrush(brush)
        self.previousPos = self.scenePos()
        self.isMoving = False

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange and self.scene():
            sceneRect = self.scene().sceneRect()
            rect = self.boundingRect()
            widthHalf = rect.width() / 2.0
            heightHalf = rect.height() / 2.0
            topLeft = value - QPointF(widthHalf, heightHalf)
            bottomRight = value + QPointF(widthHalf, heightHalf)
            if not sceneRect.contains(topLeft) or not sceneRect.contains(bottomRight):
                y = value.y()
                x = value.x()
                if y < sceneRect.top() + heightHalf:
                    y = sceneRect.top() + heightHalf
                if y > sceneRect.bottom() - heightHalf:
                    y = sceneRect.bottom() - heightHalf
                if x < sceneRect.left() + widthHalf:
                    x = sceneRect.left() + widthHalf
                if x > sceneRect.right() - widthHalf:
                    x = sceneRect.right() - widthHalf
                value.setX(x)
                value.setY(y)
                return value
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        scenePos = event.scenePos()
        if event.button() == Qt.MouseButton.LeftButton:
            self.previousPos = self.scenePos()
            self.isMoving = True
        elif event.button() == Qt.MouseButton.RightButton and not self.isMoving:
            startPoint = self.scenePos()
            line = LineItem()
            line.setSceneLine(startPoint, scenePos)
            self.scene().addItem(line)

            self.scene().connect(line, self)
            line.grabMouse()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isMoving:
            self.scene().moveLinesOfRect(self)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if len(self.findCollidingRects()) > 0:
                self.setPos(self.previousPos)
                self.scene().moveLinesOfRect(self)
            self.isMoving = False

        super().mouseReleaseEvent(event)

    def findCollidingRects(self):
        collidingItems = self.collidingItems()

        return list(filter(lambda item: isinstance(item, RectItem), collidingItems))


class LineItem(QGraphicsLineItem):
    def __init__(self):
        super().__init__()

        pen = QPen()
        pen.setWidth(5)
        pen.setColor(QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        self.setPen(pen)
        self.setZValue(1)

    def setSceneLine(self, startPoint, endPoint):        
        self.setPos(startPoint)
        # setLine принимает локальные координаты в системе координат ЛИНИИ
        self.setLine(QLineF(QPointF(0.0, 0.0), self.mapFromScene(endPoint)))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.scene().removeLine(self)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            scenePos = event.scenePos()
            grabbedItem = self.scene().mouseGrabberItem()
            rects = self.scene().getRectsByLine(self)
            if self == grabbedItem and len(rects) == 1:
                rect = self.scene().getRectFromPosition(scenePos)
                self.ungrabMouse()
                if rect:
                    rectCenter = rect.scenePos()
                    self.setSceneLine(self.scenePos(), rectCenter)

                    self.scene().connect(self, rect)
                else:
                    self.scene().removeLine(self)
                    return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        rects = self.scene().getRectsByLine(self)
        if len(rects) == 1:
            self.setSceneLine(self.scenePos(), event.scenePos())
        super().mouseMoveEvent(event)


class RectLineIndex:
    def __init__(self):
        self.linesByRect = {}
        self.rectsByLine = {}

    def connect(self, line, rect):
        if line in self.rectsByLine:
            if rect not in self.rectsByLine[line]:
                self.rectsByLine[line].append(rect)
        else:
            self.rectsByLine[line] = [rect]

        if rect in self.linesByRect:
            if line not in self.linesByRect[rect]:
                self.linesByRect[rect].append(line)
        else:
            self.linesByRect[rect] = [line]

    def removeLine(self, line):
        def filterFunc(itemLine):
            return itemLine != line

        if line in self.rectsByLine:
            rects = self.rectsByLine[line]
            del self.rectsByLine[line]
            for rect in rects:
                self.linesByRect[rect] = list(filter(filterFunc, self.linesByRect[rect]))

    def getLinesByRect(self, rect):
        return self.linesByRect.get(rect, [])

    def getRectsByLine(self, line):
        return self.rectsByLine.get(line, [])


class GraphicsScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.index = RectLineIndex()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scenePos = event.scenePos()

            rect = QRectF(-RectItem.WIDTH / 2, -RectItem.HEIGHT / 2, RectItem.WIDTH, RectItem.HEIGHT)
            rectItem = RectItem()
            rectItem.setRect(rect)
            rectItem.setPos(scenePos)

            self.addItem(rectItem)

            topLeft = scenePos - QPointF(RectItem.WIDTH / 2, RectItem.HEIGHT / 2)
            bottomRight = scenePos + QPointF(RectItem.WIDTH / 2, RectItem.HEIGHT / 2)

            if (len(rectItem.findCollidingRects()) > 0 or
                (not self.sceneRect().contains(topLeft)) or
                (not self.sceneRect().contains(bottomRight))
            ):
                self.removeItem(rectItem)

        super().mouseDoubleClickEvent(event)

    def getRectFromPosition(self, scenePos):
        items = self.items(scenePos)

        def filterFunc(item):
            return isinstance(item, RectItem)

        return next(filter(filterFunc, items or []), None)

    def moveLinesOfRect(self, movingRect):
        lineItems = self.index.getLinesByRect(movingRect)
        for lineItem in lineItems:
            rects = self.index.getRectsByLine(lineItem)
            if len(rects) == 2:
                begin = rects[0]
                end = rects[1]

                lineItem.setSceneLine(begin.scenePos(), end.scenePos())

    def connect(self, line, rect):
        self.index.connect(line, rect)

    def getRectsByLine(self, line):
        return self.index.getRectsByLine(line)

    def removeLine(self, line):
        self.index.removeLine(line)
        self.removeItem(line)


class GraphicsView(QGraphicsView):
    def __init__(self):
        super().__init__()
        scene = GraphicsScene()
        self.setScene(scene)
        self.setMinimumSize(800, 600)

    def drawBackground(self, painter, rect):
        painter.fillRect(self.scene().sceneRect(), QBrush(QColor('lightyellow')))

    def resizeEvent(self, event):
        self.scene().setSceneRect(0, 0, 800, 600)
        self.fitInView(0, 0, 800, 600, Qt.AspectRatioMode.KeepAspectRatio)
        super().resizeEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drawer")
        self.view = GraphicsView()
        self.setCentralWidget(self.view)


def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
