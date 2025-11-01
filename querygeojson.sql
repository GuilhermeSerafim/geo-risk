[out:json][timeout:120];
area["name"="Curitiba"]["boundary"="administrative"]["admin_level"="8"]->.a;

(
  way(area.a)["waterway"~"river|canal"];
  relation(area.a)["waterway"~"river|canal"];
  way(area.a)["natural"="water"]["water"~"reservoir|lake"];
  relation(area.a)["natural"="water"]["water"~"reservoir|lake"];
);
out geom;
