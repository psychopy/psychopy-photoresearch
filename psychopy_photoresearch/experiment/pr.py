try:
    from psychopy.experiment.monitor import BasePhotometerDeviceBackend
except ModuleNotFoundError:
    BasePhotometerDeviceBackend = object

class SpectroScanPRDeviceBackend(BasePhotometerDeviceBackend):
    backendLabel = "PR Series"
    deviceClass = "psychopy_photoresearch.hardware.pr.SpectroScanPRPhotometerDevice"

    def getParams(self):
        return [], {}

    def writeDeviceCode(self, buff):
        # write core code
        BasePhotometerDeviceBackend.writeBaseDeviceCode(self, buff, close=True)
