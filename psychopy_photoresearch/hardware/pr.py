import re
import time
from psychopy import logging
from psychopy.clock import Clock
from psychopy.tools import systemtools
from psychopy.hardware.serialdevice import SerialDevice
from psychopy.hardware.photometer import BasePhotometerDevice, PhotometerResponse


class SpectroScanPRPhotometerResponse(PhotometerResponse):
    fields = PhotometerResponse.fields + ["dur", "cie", "spd", "temp"]

    def __init__(
            self, 
            t, 
            value, 
            dur=None, 
            lum=None, 
            cie=None, 
            spd=None, 
            temp=None, 
            device=None
        ):
        PhotometerResponse.__init__(
            self,
            t=t,
            value=value,
            device=device
        )
        # store extras
        self.dur = dur
        self.lum = lum
        self.cie = cie
        self.spd = spd
        self.temp = temp


class SpectroScanPRSerialDevice(SerialDevice):
    """
    Because the SpectroScan PR series can only handle 1 char at a time, we need a special serial interface for it
    """
    def sendMessage(self, message):
        # split message into individual letters
        for letter in message:
            # send each letter
            self.com.write(
                letter.encode("utf-8")
            )
            # sleep between each
            time.sleep(0.1)
        # send eol
        if not message.endswith("\n"):
            self.com.write(b"\n")
        # sleep after message
        time.sleep(0.1)
        


class SpectroScanPRPhotometerDevice(BasePhotometerDevice):

    responseClass = SpectroScanPRPhotometerResponse

    def __init__(self, port):
        BasePhotometerDevice.__init__(self)
        # setup serial connection
        self.com = SpectroScanPRSerialDevice(
            port=port, 
            baudrate=9600,
            eol=b"\n",
            pauseDuration=0.1
        )
        # put device in remote mode
        self.com.sendMessage("PHOTO")
        self.com.awaitResponse()
        # get device type
        self.com.sendMessage("D111")
        self.deviceType = self.com.awaitResponse()
        print(self.deviceType)
        # start a timer
        self.clock = Clock()
    
    def __del__(self):
        if hasattr(self, "com"):
            self.com.sendMessage("Q")
            self.com.awaitResponse()
            
    def dispatchMessages(self, spd=False):
        """
        When called, dispatch a single reading.

        Parameters
        ----------
        spd : bool
            If True, request the full SPD mapping (this could take up to 240s)
        """
        # dict to store data in
        message = {
            't': self.clock.getTime()
        }
        # request measurement
        self.com.sendMessage('M0')
        self.com.awaitResponse(timeout=30)
        time.sleep(1)
        # get XY
        self.com.sendMessage("D1")
        message['xy'] = self.com.awaitResponse()
        # get CIE 1931 Tristimulus values
        self.com.sendMessage("D2")
        message['tristim'] = self.com.awaitResponse()
        # get UV
        self.com.sendMessage("D3")
        message['uv'] = self.com.awaitResponse()
        # get color temp
        self.com.sendMessage("D4")
        message['temp'] = self.com.awaitResponse()
        # get spd
        if spd:
            self.com.sendMessage("D5")
            message['spd'] = self.com.awaitResponse(multiline=True)
        else:
            message['spd'] = None
        # store how long it took
        message['dur'] = self.clock.getTime() - message['t']

        self.receiveMessage(
            self.parseMessage(message)
        )

    def parseMessage(self, message):
        def parse_string(value, field):
            """
            Parse a string containing 5 floats (sent by the device) into a list of 5 floats.

            Parameters
            ----------
            value : str
                String containing 5 floats

            Returns
            -------
            list[float]
                List of floats
            """
            
            try:
                assert value is not None, f"Received no value for {field}"
                # split and convert to float
                output = [
                    float(val) 
                    for val in value.replace("\r\n", "").split(",")
                ]
                # should be 5 values
                assert len(output) == 5, f"Expected 5 {field} values, got {uv}"
            except (ValueError, AssertionError) as err:
                # log error rather than raising
                logging.error(
                    f"Failed to parse message for {field}, reason: {err}"
                )
                # return None for everything if failed
                output = [None, None, None, None, None]
            
            return output
            
        # create object to store response init values
        data = {
            't': message['t'],
            'value': None,
            'dur': message['dur'],
            'cie': {
                'uv': None,
                'xy': None,
                'tristim': None
            },
            'temp': None,
            'spd': None,
            'device': self
        }
        # parse UV
        uv = parse_string(message['uv'], field="CIE UV")
        data['cie']['uv'] = (uv[3], uv[4])
        data['value'] = uv[2]
        # parse XY
        xy = parse_string(message['xy'], field="CIE XY")
        data['cie']['xy'] = (xy[3], xy[4])
        # parse tristim
        tristim = parse_string(message['tristim'], field="CIE Tristim")
        data['cie']['tristim'] = (tristim[2], tristim[3], tristim[4])
        # parse spectrum
        if message['spd']:
            data['spd'] = {}
            for row in message['spd']:
                try:
                    key, val = row.replace("\r", "").strip().split(",", 1)
                    data['spd'][int(key)] = float(val)
                except:
                    # skip any rows which fail
                    continue
        else:
            data['spd'] = None
        # parse temperature
        temp = parse_string(message['temp'], field="color temperature")
        data['temp'] = temp[3]
        
        return PRSeriesPhotometerResponse(**data)
    
    def isSameDevice(self, other):
        return False

    @staticmethod
    def getAvailableDevices():
        profiles = []
        # use windows profiler to get all serial devices
        for device in systemtools.systemProfilerWindowsOS(
            classid="{4d36e978-e325-11ce-bfc1-08002be10318}",
            connected=True
        ):
            # filter only for those which look like a PR series
            if device['Manufacturer Name'] == "Photo Research Inc":
                # get port
                port = re.match(
                    pattern=r"PRI Instrument \((COM\d+)\)",
                    string=device['Device Description']
                ).group(1)
                # construct profile
                profiles.append({
                    'deviceName': f"PRSeries@{port}",
                    'deviceClass': "psychopy_photoresearch.hardware.pr.PRSeriesPhotometerDevice",
                    'port': port
                })
        
        return profiles
       