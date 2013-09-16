ddp-stage-1-and-openbts
=======================

dual degree stage 1 and openbts

Target: Sense the presence of calls going on in the primary OpenBTS and as soon as the call drops/ends start the secondary OpenBTS to enable communication among secondary users

Details:

We sensed the energy of the uplink frequency (usually --- uplink freq = downlink freq - 45MHz --- in the GSM900 band) using GnuRadio. We observed the energy of the uplink frequency is lower when there are no calls. We selected a threshold energy level and let the secondary OpenBTS start as soon as the primary OpenBTS's energy level went below threshold.