import math
import random

from kivy.app import App

from kivy.network.urlrequest import UrlRequest

from kivy_garden.mapview import MapView, MapLayer, MarkerMapLayer, MapMarker, MarkerMapLayer
from kivy.app import App
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.uix.label import Label

from pyproj import Transformer

def get_transformer_GPS2XY():
    return Transformer.from_crs("epsg:4326", "epsg:3857")

def convert_projection(center, delta, factor):
    transformerGPS2XY = get_transformer_GPS2XY()
    transformerXY2GPS = Transformer.from_crs("epsg:3857", "epsg:4326")
    lat, lon = center
    x, y = transformerGPS2XY.transform(lon, lat)
    dx, dy = delta

    return transformerXY2GPS.transform(x + factor * dx, y + factor * dy)


class GameConfig:
    osrm_url="http://lightnup.schaefer-christian.de:5000/nearest/v1/foot"
    player_file="player.png"
    light_file="light.png"
    treasure_file="treasure.png"
    collect_radius_m=15
    visibility_radius_m=50
    game_centers = [(9.03, 48.40),]
    game_zoom = 18
    lightnup = 20
    light_decay_per_walk = 1
    player_step_size_m = 20
    game_window = (500,500)


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
            Color(0, 0, 0, 0.7)
            
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


class LevelIndicatorLayer(MapLayer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.level_text = Label(text="Level x")
        self.level_text.font_size = 30
        self.add_widget(self.level_text)

    def set_level(self, level_num):
        self.level_text.text = f"Level {level_num}"


class SnappableMapMarker(MapMarker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.snap_request()

    def snap_request(self):
        request_url = f"{GameConfig.osrm_url}/{self.lon},{self.lat}"
        _ = UrlRequest(url=request_url, on_success=self.snap)

    def snap(self, req, result):
        if result["code"] == "Ok":
            location = result["waypoints"][0]["location"]
            self.lon, self.lat = location
            if self.parent is not None:
                self.parent.reposition()


class ImagePlayer(SnappableMapMarker): # careful here!
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source = GameConfig.player_file
        self.width = 20
        self.anchor_x, self.anchor_y = (0.5, 0.5)

    def snap(self, req, result):
        result = super().snap(req, result)
        self.parent.parent.light_cone.reposition()
        return result


class ImageTreasure(SnappableMapMarker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source = GameConfig.treasure_file
        self.width = 20
        self.anchor_x, self.anchor_y = (0.5, 0.5)

    
class LightCone(MarkerMapLayer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.collect_radius_m = GameConfig.collect_radius_m
        self.visibility_radius_m = GameConfig.visibility_radius_m

    def get_distance_to_object(self, obj):
        lon, lat = self.parent.player.lon, self.parent.player.lat
        transformer = get_transformer_GPS2XY()
        pos_player = transformer.transform(lon, lat)
        pos_obj = transformer.transform(obj.lon, obj.lat)
        return math.dist(pos_player, pos_obj)

    def is_within_collect(self, object):
        dist = self.get_distance_to_object(object)
        return dist <= self.collect_radius_m

    def is_within_visibility(self, object):
        dist = self.get_distance_to_object(object)
        return dist <= self.visibility_radius_m

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
            Color(1, 1, 0, 0.25)
            
            Ellipse(pos=(cwx,csy), size=(cex-cwx, cny-csy))

            Ellipse(pos=(vwx,vsy), size=(vex-vwx, vny-vsy))
        

class ImageLight(SnappableMapMarker):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source = GameConfig.light_file
        self.width = 50
        self.anchor_x, self.anchor_y = (0.5, 0.5)
        

class FeatureLayer(MarkerMapLayer):
    def __init__(self, center, size_m, num_items, **kwargs):
        super().__init__(**kwargs)

        self.features = list()

        for i in range(num_items+1):
            dx, dy = size_m
            dx *= 0.5-random.random()
            dy *= 0.5-random.random()
            lat, lon = convert_projection(center=center, delta=(dx,dy), factor=1)
            if i == 0:
                feature = ImageTreasure(lon=lon, lat=lat)
            else:
                feature = ImageLight(lon=lon, lat=lat)
            self.features += [feature]
            self.add_widget(feature)

    def update_features_by_player(self):
        light_cone = self.parent.light_cone

        new_features = list()

        for feature in self.features:
            if light_cone.is_within_collect(feature):
                if isinstance(feature, ImageTreasure):
                    self.parent.level_up()
                elif isinstance(feature, ImageLight):
                    light_cone.visibility_radius_m += GameConfig.lightnup
                    light_cone.reposition()
                self.remove_widget(feature)
            else:
                new_features += [feature]
                if light_cone.is_within_visibility(feature):
                    feature.opacity = 1
                else:
                    feature.opacity = 0

        self.features = new_features

        self.reposition()

            
class LevelWidget(MapView):
    def __init__(self, level, **kwargs) -> None:
        super().__init__(**kwargs)

        self.level = level
        self.game_center = GameConfig.game_centers[0]
        self.game_zoom = GameConfig.game_zoom

        self.player_step_size_m = GameConfig.player_step_size_m

        self.lon, self.lat = self.game_center

        self.size_m = GameConfig.game_window
        self.zoom = self.game_zoom

        self.feature_layer = None

        self.player = ImagePlayer(lon=self.lon, lat=self.lat)
        self.add_marker(self.player)
        
        self.game_box = GameBox(center=self.game_center, size_m=self.size_m)
        self.add_layer(self.game_box)

        self.light_cone = LightCone()
        self.add_layer(self.light_cone)

        self.level_indicator_layer = LevelIndicatorLayer()
        self.add_layer(self.level_indicator_layer)
        self.level_indicator_layer.set_level(self.level)

        self.reseed_features(initial=True)

        self.feature_layer.update_features_by_player()         

    def reseed_features(self, num_features=10, initial=False):
        if not initial:
            self.remove_layer(self.feature_layer)
        self.feature_layer = FeatureLayer(center=self.game_center,
                                          size_m=self.size_m,
                                          num_items=num_features)
        self.add_layer(self.feature_layer, mode="window")

    def level_up(self):
        screenmanager = self.parent.parent
        screenmanager.current = "levelup"

    def on_touch_up(self, touch):
        return True

    def on_touch_down(self, touch):

        self.walk(touch.pos)
        
        return True

    def walk(self, pos):

        self.light_cone.visibility_radius_m = max(0, self.light_cone.visibility_radius_m-GameConfig.light_decay_per_walk)

        if self.light_cone.visibility_radius_m <= 0:
            screenmanager = self.parent.parent
            screenmanager.current = "gameover"

        x, y = pos

        px, py = self.player.center

        dx = x - px
        dy = y - py

        dist = math.sqrt(dx**2 + dy**2) + 0.001  # We dont want to divide by zero

        dx /= dist
        dy /= dist

        dx *= self.player_step_size_m
        dy *= self.player_step_size_m

        lon, lat = self.player.lon, self.player.lat

        self.player.lat, self.player.lon = convert_projection((lon, lat), (dx, dy), factor=1)

        self.player.snap_request()

        self._default_marker_layer.reposition()
        self.light_cone.reposition()

        self.feature_layer.update_features_by_player()

