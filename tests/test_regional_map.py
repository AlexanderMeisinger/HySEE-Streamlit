"""Run with python -m unittest discover -s tests from HySEE-Streamlit."""

import io
import json
import unittest
import plotly.graph_objects as go

from regional_map import (
    DEFAULT_BASEMAP, POTENTIAL, build_spatial_map, read_network, read_potential, read_regions,
)


class SpatialMapTests(unittest.TestCase):
    def setUp(self):
        self.data = read_potential(io.StringIO(
            "region,country,latitude,longitude,potential_twh_per_year\n"
            "01,BG,42,25,0\n02,RO,45,26,12\n"
        ))
        self.edges = read_network(io.StringIO(
            "bus0,bus1,carrier,capacity_gw\n01,02,H2,4\n01,02,AC,2\n"
        ), self.data)
        self.geo = read_regions(io.StringIO(json.dumps({
            "type": "FeatureCollection", "features": [{
                "type": "Feature", "properties": {"name": name},
                "geometry": {"type": "Polygon", "coordinates": [
                    [[24, lat], [25, lat], [25, lat + 1], [24, lat + 1], [24, lat]]
                ]},
            } for name, lat in [("01", 42), ("02", 45)]]
        })))

    def test_layers_and_zero_potential(self):
        fig = build_spatial_map(self.data, self.geo, self.edges, POTENTIAL, "Hydrogen Network", POTENTIAL)
        suffix = "" if hasattr(go, "Choroplethmap") else "box"
        self.assertEqual([t.type for t in fig.data], ["choroplethmap" + suffix, "scattermap" + suffix, "scattermap" + suffix])
        self.assertEqual(fig.layout["map" + suffix].style, DEFAULT_BASEMAP)
        self.assertEqual(list(fig.data[0].z), [0, 12])
        self.assertGreater(fig.data[-1].marker.size[0], 0)
        self.assertEqual(list(fig.data[1].lat), [42, 45])
        self.assertTrue(fig.to_json())

    def test_all_layer_combinations(self):
        for regions in ("Nothing", POTENTIAL):
            for network in ("Nothing", "Hydrogen Network", "Electricity Network"):
                for nodes in ("Nothing", POTENTIAL):
                    fig = build_spatial_map(self.data, self.geo, self.edges, regions, network, nodes)
                    self.assertEqual(len(fig.data), 1 + (network != "Nothing") + (nodes != "Nothing"))
                    fig.to_json()

    def test_country_filter_omits_cross_border_edge(self):
        fig = build_spatial_map(self.data.iloc[:1], self.geo, self.edges, POTENTIAL, "Hydrogen Network", POTENTIAL)
        self.assertEqual(len(fig.data), 2)
        self.assertEqual(list(fig.data[0].locations), ["01"])

    def test_nodes_without_optional_data(self):
        fig = build_spatial_map(self.data, None, None, "Nothing", "Nothing", POTENTIAL)
        self.assertEqual(len(fig.data), 1)

    def test_rejects_unknown_endpoint_and_invalid_capacity(self):
        for row in ("01,missing,H2,4", "01,02,H2,-1", "01,02,H2,inf"):
            with self.assertRaises(ValueError):
                read_network(io.StringIO("bus0,bus1,carrier,capacity_gw\n" + row), self.data)

    def test_rejects_invalid_geometry(self):
        self.geo["features"][0]["geometry"] = {"type": "Point", "coordinates": [25, 42]}
        with self.assertRaises(ValueError):
            read_regions(io.StringIO(json.dumps(self.geo)))

    def test_rejects_duplicate_polygon_ids(self):
        self.geo["features"][1]["properties"]["name"] = "01"
        with self.assertRaises(ValueError):
            read_regions(io.StringIO(json.dumps(self.geo)))


if __name__ == "__main__":
    unittest.main()
