# HFDL.observer/888

A multi-headed dumphfdl receiver for use with Web-888 devices.

## Background

The dynamism of the High Frequency Data Link infrastructure poses some problems for those trying to efficiently monitor these packets. There are a wide variety of frequencies in use across the HF spectrum (in this case, between 2.5 and 22MHz). The active frequencies change depending on time of day, ionospheric conditions, and the associated ground station. Picking the correct frequencies, and switching between them is a challenge. This challenge is magnified as many available SDRs have limited sample rates, and cannot scan the entire available HFDL frequency space.

Enter [RX-888 (mk2)](https://www.rx-888.com/rx/) and [Web-888](https://www.rx-888.com/web/) devices. These are advanced, yet still affordable, SDRs that can process the entire HF spectrum at the same time. 

Unfortunately, the RX-888 (mk2) suffers from limited driver availability for Linux, which is a common platform for HFDL hobbyists. HFDL stations are frequently lower power devices such as odroids, raspberry pi and the like which may not have the CPU necessary to deal with the firehose of data from the RX-888 mk2.

The Web-888 offers a solution for that. It combines the receiver of an RX-888 mk2 with an FPGA programmed to do bulk processing of data, and an KiwiSDR compatible web interface, based on [Beagle SDR](https://github.com/jks-prv/Beagle_SDR_GPS) from which KiwiSDR is also derived. It offers 13 simultaneous streams/channels to process. Each channel is fairly narrow (12kHz) but that is enough to cover up to 4 HFDL frequencies (if they are close enough together).

## Features

HFDL.observer/888 makes using a Web-888 device to receive HFDL packets (and share them with airframes.io, or other consumers) easy.

It assigns frequencies to each of 13 virtual "receivers". The assignments are based on a list of currently active frequencies ranked by a user-configured station preference (generally stations nearer your Web-888 should have higher preference).

It manages the `kiwirecorder` web socket clients that stream the raw data from Web-888 for each virtual receiver. It also manages the `dumphfdl` processes used to decode HFDL from the raw I/Q data `kiwirecorder` emits.

It watches the decoded HFDL packets for frequency updates. When the active frequency list changes, virtual receivers may be reassigned to higher-priority frequencies.

Optionally, it can also retrieve updated frequency lists from community source (such as hfdl.observer or airframes.io). This covers periods where squitters (frequency updates) may not be received by your station for a time.

In general, there are around 30 frequencies active globally at a given time. HFDL.observer/888 allows your station to monitor (typically) 18-23 of them.

Processing the entire HF frequency space would be very CPU-intensive. Taking advantage of the FPGA in Web-888 to select only the portions we're interested in means:

- The data rate from the Web-888 to the device running HFDL.observer/888 is around 5Mbps.
- The aggregate bandwidth that needs to be scanned by all virtual receivers is around 156kHz.
- The CPU required for the virtual receivers is about ½ of 1 core of an Odroid M1S or Raspberry Pi4 (~13% total CPU)

## CUI

HFDL.observer/888 also adds a simple but rich console-based display. At the top is a heat map like grid depicting the frequencies currently (or recently) being observed, and packet counts for each minute. Below that is log output. As it is console based, it can run within a `screen` session over `ssh` from a remote computer.

This is a bit more CPU intensive, taking about the same CPU as all of the virtual receivers combined. It can be disabled, and is disabled by default when it is run as a (systemd) service.

## Setting up the Web-888

To start, follow the [basic set up instructions](https://www.rx-888.com/web/guide/requirements.html) on the Web-888 site. You'll need to put the ROM image on a micro-SD card. There's little activity and little use of space, so you should not go overboard on a card (in fact, don't use anything 32GB or larger, as the device will be unable to read it).

You do not have to configure any of the "public" options -- you aren't going to be sharing this device to the public. You should make sure its location is configured correctly, though. This can be done automatically if you've attached a GPS antenna.

There are only a few settings that are of interest.

### Control Tab

- `HF Bandwidth Selection`: select 32M. Using 64M will disable 1 channel (leaving only 12).
- `Disable waterfalls/spectrum?`: YES. No web clients will be using this device, and you can save a bit of processing power.
- `Switch between HF or Air Band`: Select HF

### Config Tab

- `Enable ADC PGA?`: your choice. It's safe to try either for a period.
- `Correct ADC clock by GPS PPS`: YES if you have a GPS antenna connected.
- `Enable ADC Dithering`: NO. This does not help the I/Q processing dumphfdl does.

### Public Tab

- `Register on www.rx-888.com/web/rx?`: NO. You're using this device exclusively for your own private use. Even if you need to access it over public Internet, you don't need it to register with the available public servers.


## Installation

Installation can be performed on `apt`-equipped systems (Debian, Ubuntu, Armbian, etc.) by using the provided `install.sh` command. The installation requires `sudo` access so that it can install packages and dependencies.

```
$ git clone https://github.com/hfdl-observer/hfdlobserver888
$ cd hfdlobserver888
$ ./install.sh
```

Formal releases are not made at this time, so `main` off of the repository is the best source. Releases will come eventually.

### Breakdown

The install script automates the following steps:

1. Installing necessary basic packages: `whiptail python3 python3-venv git`
2. Set up a virtual environment, and activate it.
3. Install Python requirements (from `requirements.txt`) into the virtual environment using `pip`.
4. Download `kiwiclient` to a known location.
5. Install `dumphfdl` (and dependencies)
   1. Install package dependencies: `build-essential cmake pkg-config libglib2.0-dev libconfig++-dev libliquid-dev libfftw3-dev zlib1g-dev libxml2-dev libjansson-dev`
   2. clone `libacars`, build, and install it.
   3. clone `statsd-c-client`, build, and install it.
   4. clone `dumphfdl`, build, and install it.
6. Run `./configure.py` to walk through some simple configuration questions.

While several helper programs are installed, they are invoked via the operating system, HFDL.observer/888 makes no alteration to any of their code or operations, and connects only through standard mechanisms (file handles and sockets).

## Configuration

Configuration is provided by a YAML formatted file. By default, and normally, it is `settings.yaml`.

The provided `./configure.py` script asks a number of questions to provide basic configuration. For most users, this should suffice. The `src/settings.py` file contains a commented system default settings dialog for the curious, or those in need of more complex configurations. This is still in some flux, but the basic `settings.yaml` structure should be stable.

You can rerun `configure.py` at any time, and it will walk you through the questions again; subsequent runs will write to `settings.yaml.new` so you can compare and merge the files if you desire.

The configuration tool provides two options for setting the ranked order of HFDL stations.

1. You can provide a comma-separated list of station IDs. You can see the station IDs and some related information at the [HFDL.observer](https://hfdl.observer) site.

2. The configuration tool can "guess" the station ranking. It builds this list using distance from your Web-888's location. You will have to enter it. Generally entering just the rounded degrees latitude and longitude should be sufficient.

The distance tool is also available as

```
$ extras/guess_station_ranking.py <lat> <lon>
```

## Running

Once configured, you can run the receiver by

```
$ <path-to>/hfdlobserver888.sh
```

if you do not want the "fancy" TUI, pass in the `--headless` option. The usage is minimal, but is explained with `--help`.

Hopefully, it should Just Work.

In case of abnormal termination, you should kill any `kiwirecorder.py` instances that may be left hanging. This can be accomplished with the following:

```
$ pkill -f kiwirecorder
```

## Exiting

Press `^C` (control + C). Enhance your calm, as it can take a couple of seconds to shut down cleanly.

## Run as a Service (very alpha)

If you want to run this as a service, you can run the script to install the service file for systemd.

```
$ extras/install-service.sh
```

It then becomes a normal service named `hfdlobserver888`. Following the usual pattern, there is a very minor ability to configure it via `/etc/default/hfdlobserver888`, but most items are managed through the `settings.yaml` file.

## Acknowledgements

- [dumphfdl](https://github.com/szpajder/dumphfdl) - an excellent decoder of HFDL signals
- [kiwiclient](https://github.com/jks-prv/kiwiclient) - used to stream data from Web-888 to dumphfdl
- [airframes.io](https://airframes.io/) - a great community of people interested in data from the sky.
- [libacars](https://github.com/szpajder/libacars) - used by dumphfdl to parse ACARS data from HFDL packets
- [stats-d-client](https://github.com/romanbsd/statsd-c-client.git) - used to optionally send statsd statistics.