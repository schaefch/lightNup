import random

from kivy.app import App

from kivy.network.urlrequest import UrlRequest

from kivy_garden.mapview import MapView, MapLayer, MarkerMapLayer, MapMarker, MarkerMapLayer
from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.uix.image import Image

from pyproj import Transformer


def convert_projection(center, delta, factor):
    transformerGPS2XY = Transformer.from_crs("epsg:4326", "epsg:3857")
    transformerXY2GPS = Transformer.from_crs("epsg:3857", "epsg:4326")
    lat, lon = center
    x, y = transformerGPS2XY.transform(lon, lat)
    dx, dy = delta

    return transformerXY2GPS.transform(x + factor * dx, y + factor * dy)


class GameBox(MapLayer):
    def __init__(self, center, size_m, **kwargs):
        super().__init__(**kwargs)
        self.center = center
        self.size_m = size_m

        self.upper_right = self.project(factor=0.5)
        self.lower_left = self.project(factor=-0.5)

    def project(self, factor):
        return convert_projection(self.center, self.size_m, factor=factor)

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

            # Right
            if _east > east:
                Rectangle(pos=(ex, 0), size=(vx-ex, vy))


class LightCone(MapLayer):
    def __init__(self, start, **kwargs):
        super().__init__(**kwargs)
        self.cone_center = start


class ImageLight(MapMarker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source = "light.png"
        self.width = 50
        self.anchor_x, self.anchor_y = (0.5, 0.5)
        self.make_request()

    def make_request(self, url="http://lightnup.schaefer-christian.de:5000/nearest/v1/foot"):
        request_url = f"{url}/{self.lon},{self.lat}"
        _ = UrlRequest(url=request_url, on_success=self.snap)

    def snap(self, req, result):
        if result["code"] == "Ok":
            location = result["waypoints"][0]["location"]
            self.lon, self.lat = location
            

class FeatureLayer(MarkerMapLayer):
    def __init__(self, center, size_m, num_items, **kwargs):
        super().__init__(**kwargs)

        for _ in range(num_items):
            dx, dy = size_m
            dx *= 0.5-random.random()
            dy *= 0.5-random.random()
            lat, lon = convert_projection(center=center, delta=(dx,dy), factor=1.0)
            self.add_widget(ImageLight(lon=lon, lat=lat))

            
class LevelWidget(MapView):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.level = 1
        self.game_center = (9.03, 48.40)

        self.lon, self.lat = self.game_center

        self.size_m = (500, 500)
        self.zoom = 18

        self.feature_layer = None

        self.game_box = GameBox(center=self.game_center, size_m=self.size_m)
        self.light_cone = LightCone(start=self.center)

        self.add_layer(self.game_box)
        self.add_layer(self.light_cone)

        self.reseed_features(initial=True)             

    def reseed_features(self, num_features=10, initial=False):
        if not initial:
            self.remove_layer(self.feature_layer)
        self.feature_layer = FeatureLayer(center=self.game_center,
                                          size_m=self.size_m,
                                          num_items=num_features)
        self.add_layer(self.feature_layer, mode="window")


class MainApp(App):
    def build(self):
        widget = LevelWidget()
        return widget

MainApp().run()
