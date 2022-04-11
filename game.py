import math
import random

from kivy.app import App

from kivy.network.urlrequest import UrlRequest

from kivy_garden.mapview import MapView, MapLayer, MarkerMapLayer, MapMarker, MarkerMapLayer, MapSource
from kivy.app import App
from kivy.graphics import Color, Rectangle, Ellipse

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


class SnappableMapMarker(MapMarker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.snap_request()

    def snap_request(self, url="http://lightnup.schaefer-christian.de:5000/nearest/v1/foot"):
        request_url = f"{url}/{self.lon},{self.lat}"
        _ = UrlRequest(url=request_url, on_success=self.snap)

    def snap(self, req, result):
        if result["code"] == "Ok":
            location = result["waypoints"][0]["location"]
            self.lon, self.lat = location
            self.parent.reposition()


class ImagePlayer(SnappableMapMarker): # careful here!
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source = "player.png"
        self.width = 20
        self.anchor_x, self.anchor_y = (0.5, 0.5)

    
class LightCone(MarkerMapLayer):
    def __init__(self, collect_radius_m=30, visiblity_radius_m=50, **kwargs):
        super().__init__(**kwargs)
        self.collect_radius_m = collect_radius_m
        self.visibility_radius_m = visiblity_radius_m

    def reposition(self):
        self.canvas.clear()
        super().reposition()
        mapview = self.parent

        center = (self.parent.player.lon, self.parent.player.lat)

        cw, cs = convert_projection(center, 2*[self.collect_radius_m], factor=-1)
        ce, cn = convert_projection(center, 2*[self.collect_radius_m], factor=1)
        cwx, csy = mapview.get_window_xy_from(cw, cs, zoom=mapview.zoom)
        cex, cny = mapview.get_window_xy_from(ce, cn, zoom=mapview.zoom)

        vw, vs = convert_projection(center, 2*[self.visibility_radius_m], factor=-1)
        ve, vn = convert_projection(center, 2*[self.visibility_radius_m], factor=1)
        vwx, vsy = mapview.get_window_xy_from(vw, vs, zoom=mapview.zoom)
        vex, vny = mapview.get_window_xy_from(ve, vn, zoom=mapview.zoom)

        with self.canvas:
            # Add a red color
            Color(0, 0, 1., 0.25)
            
            Ellipse(pos=(cwx,csy), size=(cex-cwx, cny-csy))

            Ellipse(pos=(vwx,vsy), size=(vex-vwx, vny-vsy))
        

class ImageLight(SnappableMapMarker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source = "light.png"
        self.width = 50
        self.anchor_x, self.anchor_y = (0.5, 0.5)
        

class FeatureLayer(MarkerMapLayer):
    def __init__(self, center, size_m, num_items, **kwargs):
        super().__init__(**kwargs)

        self.features = list()

        for _ in range(num_items):
            dx, dy = size_m
            dx *= 0.5-random.random()
            dy *= 0.5-random.random()
            lat, lon = convert_projection(center=center, delta=(dx,dy), factor=1.0)
            feature = ImageLight(lon=lon, lat=lat)
            self.features += [feature]
            self.add_widget(feature)

            
class LevelWidget(MapView):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.level = 1
        self.game_center = (9.03, 48.40)
        self.game_zoom = 17

        self.player_step_size_m = 20

        self.lon, self.lat = self.game_center

        self.size_m = (500, 500)
        self.zoom = self.game_zoom

        self.feature_layer = None

        self.player = ImagePlayer(lon=self.lon, lat=self.lat)
        self.add_marker(self.player)
        
        self.game_box = GameBox(center=self.game_center, size_m=self.size_m)
        self.add_layer(self.game_box)

        self.light_cone = LightCone()
        self.add_layer(self.light_cone)

        self.reseed_features(initial=True)             

    def reseed_features(self, num_features=10, initial=False):
        if not initial:
            self.remove_layer(self.feature_layer)
        self.feature_layer = FeatureLayer(center=self.game_center,
                                          size_m=self.size_m,
                                          num_items=num_features)
        self.add_layer(self.feature_layer, mode="window")

    def level_up(self):
        self.level += 1
        self.reseed_features()

    def on_touch_up(self, touch):
        return True

    def on_touch_down(self, touch):

        self.walk(touch.pos)
        
        return True

    def walk(self, pos):
        x, y = pos

        px, py = self.player.center

        dx = x - px
        dy = y - py

        dist = math.sqrt(dx**2 + dy**2) + 0.001

        dx /= dist
        dy /= dist

        dx *= self.player_step_size_m
        dy *= self.player_step_size_m

        lon, lat = self.player.lon, self.player.lat

        self.player.lat, self.player.lon = convert_projection((lon, lat), (dx, dy), factor=1)

        self.player.snap_request()

        self._default_marker_layer.reposition()
        self.light_cone.reposition()


class MainApp(App):
    def build(self):
        widget = LevelWidget()
        return widget

MainApp().run()
