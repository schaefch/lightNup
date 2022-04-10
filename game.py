from random import random

from kivy.app import App

from kivy_garden.mapview import MapView, MapLayer
from kivy.app import App
from kivy.graphics import Color, Rectangle

from pyproj import Proj, transform

class GameBox(MapLayer):
    def __init__(self, center, size_m, **kwargs):
        super().__init__(**kwargs)
        self.center = center
        self.size_m = size_m

        self.upper_right = self.project(factor=0.5)
        self.lower_left = self.project(factor=-0.5)

    def project(self, factor):
        xyProj = Proj("epsg:3857")
        gpsProj = Proj("epsg:4326")

        lat, lon = self.center
        x, y = transform(gpsProj, xyProj, lon, lat)
        dx, dy = self.size_m

        return transform(xyProj, gpsProj, x + factor * dx, y + factor * dy)

    def reposition(self):
        mapview = self.parent
        bbox = mapview.get_bbox()

        self.canvas.clear()

        south, west = self.lower_left

        north, east = self.upper_right

        _south, _west, _north, _east = bbox

        vx, vy = mapview.width, mapview.height

        wx, sy = mapview.get_window_xy_from(south, west, zoom=mapview.zoom)

        ex, ny = mapview.get_window_xy_from(north, east, zoom=mapview.zoom)

        with self.canvas:
            # Add a red color
            Color(1., 0, 0, 0.5)
            
            # Lower
            if _south < south:
                Rectangle(pos=(wx, 0), size=(ex-wx, sy))

            # Upper
            if _north > north:
                Rectangle(pos=(wx, ny), size=(ex-wx, vy-ny))

            # Left
            if _west < west:
                Rectangle(pos=(0, 0), size=(wx, vy))

            # Left
            if _east > east:
                Rectangle(pos=(ex, 0), size=(vx-ex, vy))

            



class LevelWidget(MapView):
    def __init__(self) -> None:
        super().__init__()
        self.level = 1
        self.center = (9.03, 48.40)

        self.lon, self.lat = self.center

        self.size_m = (500, 500)
        self.zoom = 18

        self.add_layer(GameBox(center=self.center,
                               size_m=self.size_m),
                        mode="window")


class MainApp(App):
    def build(self):
        widget = LevelWidget()
        return widget

MainApp().run()
