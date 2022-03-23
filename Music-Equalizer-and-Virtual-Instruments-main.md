# Automatic Analog Defibrilator Circuit

##  **Theory of operation**
The defibrilator device stores energy over a period of time then unload it in the patient to save him from crashing, if his heart was about to stop beating.<br />
It stores the energy on a high capacitance capacitor, using a half wave rectifier to be able to interface an AC source, then switch the output on the patient, to give him a fast shock.
<br />
<br />

##  **Components**
* 3 Resisistors(10k, 10k, 100k)
* MOSFET ampilifier
* Op-Amp
* Capacitor "high capacitance"
* Electrodes
* Two-state switch
* diode

<br />

##  **How it works**
The capacitor is charged with the source, then then it switches to the patient, where the MOSFET acts as a switch and only opens up on the "R" phase of the ECG coming from the amplifier line.<br />
This way, the energy will be delivered during the "R" phase, which is the right time for it.
<br />
<br />
![machine diagram](https://github.com/Safwanmahmoud/cccc/blob/main/wiringdiagram.png)