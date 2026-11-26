# Версии проекта

Две физические реализации — по папке на каждую. Внутри папки версии лежит только её
собственное: 3D, прошивка, распиновка. Мост на ГУ у них общий, протокол кнопок и
энкодера тоже; LED-команды есть только у архивной v1.

| | **v2 — печатная панель, текущая** | **v1 — макетка, архив** |
|---|---|---|
| папка | [v2/](v2/) | [v1/](v1/) |
| 3D | [v2/modeling/](v2/modeling/) — `face.py`, `body.py`, `clamp.py`, `encoder.py`, `knob*.py`, `keycaps.py`, `print_stl.py` | [v1/modeling/](v1/modeling/) — `build_housing.py`, `keycaps/`, `knob_knurl/`, пробники |
| прошивка | [v2/firmware/knopych-panel/](v2/firmware/knopych-panel/) (v1.0) | [v1/firmware/knopych-panel/](v1/firmware/knopych-panel/) (v0.6) |
| диагностика пинов | [v2/firmware/pin-scan/](v2/firmware/pin-scan/) | — |
| распиновка | [v2/docs/pins.md](v2/docs/pins.md) | [v1/docs/pins.md](v1/docs/pins.md) |
| механика | [v2/modeling/NICHE.md](v2/modeling/NICHE.md) | [v1/modeling/MOUNTING.md](v1/modeling/MOUNTING.md), [PARAMETERS.md](v1/modeling/PARAMETERS.md) |
| ещё | — | [v1/micropython/](v1/micropython/) — первый прототип |

## Команды (из корня репозитория)

```bash
./build.sh upload                                     # текущая панель (v2)
SKETCH=v1/firmware/knopych-panel ./build.sh upload   # старая панель (v1)
SKETCH=v2/firmware/pin-scan ./build.sh upload         # диагностика пинов
./build.sh monitor                                    # журнал, Ctrl+C — выход
./build.sh listen --log                               # показывать нажатия (--gu — изображать ГУ)
```

## Что общее (лежит в корне)

- [bridge/](bridge/) — приложение-мост на ГУ; протокол один и тот же, панели отличаются
  только пинами;
- [docs/firmware.md](docs/firmware.md) — протокол и поведение прошивки;
- [docs/hardware.md](docs/hardware.md) — плата, питание, земля, чего нельзя занимать;
- [docs/gwm-api.md](docs/gwm-api.md) — интерфейс ГУ, которым пользуется мост;
- [build.sh](build.sh), [tools/](tools/).
