#!/usr/bin/env python


from gnuradio import gr, eng_notation
from gnuradio import fft
from gnuradio import blocks
from gnuradio import audio
from gnuradio import uhd
from gnuradio.eng_option import eng_option
from optparse import OptionParser
import sqlite3
import os
import sys
import math
import struct,time
import threading
from multiprocessing import Process,Value

sys.stderr.write("Warning: this may have issues on some machines+Python version combinations to seg fault due to the callback in bin_statitics.\n\n")

class ThreadClass(threading.Thread):
    def run(self):
        return

class tune(gr.feval_dd):
    def __init__(self, tb):
        gr.feval_dd.__init__(self)
        self.tb = tb

    def eval(self, ignore):
        try:
            new_freq = self.tb.set_next_freq()
            return new_freq
        except Exception, e:
            print "tune: Exception: ", e


class parse_msg(object):
    def __init__(self, msg):
        self.center_freq = msg.arg1()
        self.vlen = int(msg.arg2())
        assert(msg.length() == self.vlen * gr.sizeof_float)
        t = msg.to_string()
        self.raw_data = t
        self.data = struct.unpack('%df' % (self.vlen,), t)


class my_top_block(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self)

        usage = "usage: %prog [options] channel_freq"
        parser = OptionParser(option_class=eng_option, usage=usage)
        parser.add_option("-a", "--args", type="string", default="", help="UHD device device address args [default=%default]")
        parser.add_option("", "--spec", type="string", default=None, help="Subdevice of UHD device where appropriate")
        parser.add_option("-A", "--antenna", type="string", default=None, help="select Rx Antenna where appropriate")
        parser.add_option("-s", "--samp-rate", type="eng_float", default=1e6, help="set sample rate [default=%default]")
        parser.add_option("-g", "--gain", type="eng_float", default=None, help="set gain in dB (default is midpoint)")
        parser.add_option("", "--tune-delay", type="eng_float", default=20e-3, metavar="SECS", help="time to delay (in seconds) after changing frequency [default=%default]")
        parser.add_option("", "--dwell-delay", type="eng_float", default=1e-3, metavar="SECS", help="time to dwell (in seconds) at a given frequncy [default=%default]")
        parser.add_option("-F", "--fft-size", type="int", default=2048 , help="specify number of FFT bins [default=%default]")
        parser.add_option("", "--real-time", action="store_true", default=False, help="Attempt to enable real-time scheduling")
        parser.add_option("-d", "--decim", type="intx", default=4, help="set decimation to DECIM [default=%default]")

        (options, args) = parser.parse_args()
        if len(args) != 1:
            parser.print_help()
            sys.exit(1)
        self.channel_freq = eng_notation.str_to_num(args[0])            
        
        self.fft_size = options.fft_size
	
        if not options.real_time:
            realtime = False
        else:
            r = gr.enable_realtime_scheduling()
            if r == gr.RT_OK:
                realtime = True
            else:
                realtime = False
                print "Note: failed to enable realtime scheduling"

        self.u = uhd.usrp_source(device_addr=options.args, stream_args=uhd.stream_args('fc32'))
        
        if(options.spec):
            self.u.set_subdev_spec(options.spec, 0)
        if(options.antenna):
            self.u.set_antenna(options.antenna, 0)
            
	

        self.samp_rate = 100e6/options.decim
        samp_rate = self.samp_rate
        
        self.u.set_samp_rate(samp_rate)
	    
    	s2v = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_size)
        mywindow = fft.window.blackmanharris(self.fft_size)
        fftvar = fft.fft_vcc(self.fft_size, True, mywindow)
        
        power = 0
        for tap in mywindow:
            power += tap*tap
        c2mag = blocks.complex_to_mag_squared(self.fft_size)
#        log = blocks.nlog10_ff(10, self.fft_size, -20*math.log10(self.fft_size)-10*math.log10(power/self.fft_size))


        tune_delay  = max(0, int(round(options.tune_delay * samp_rate / self.fft_size)))  # in fft_frames
        dwell_delay = max(1, int(round(options.dwell_delay * samp_rate / self.fft_size))) # in fft_frames

        self.msgq = gr.msg_queue(16)
        self._tune_callback = tune(self)        # hang on to this to keep it from being GC'd
        stats = blocks.bin_statistics_f(self.fft_size, self.msgq, self._tune_callback, tune_delay, dwell_delay)
        if options.gain is None:
            g = self.u.get_gain_range()
            options.gain = float(g.start()+g.stop())/2.0  #        self.set_gain(options.gain)

        self.connect(self.u, s2v, fftvar, c2mag, stats)


    def set_next_freq(self):
        target_freq = self.channel_freq
        return target_freq

    def set_freq(self, target_freq):
	    self.u.set_center_freq(target_freq,0)

    def set_gain(self, gain):
        self.u.set_gain(gain,0)


def main_loop(tb):
  	tb.start()
  	
  	print 'tb.size', tb.fft_size, 'tb.channel_freq', tb.channel_freq
  	size = tb.fft_size
  	
	moving_avg_data = [0]*(size)
	count = 11
	avg_iterations = avg_iter_count = 10
	while count>0:
	    count=count-1
	    m = parse_msg(tb.msgq.delete_head())
	    if avg_iter_count > 0:
		    for i in range(0,size):
			  moving_avg_data[i] = moving_avg_data[i] + m.data[i]
		    avg_iter_count = avg_iter_count - 1
	    else: 
		    for i in range(0,len(moving_avg_data)):
			    moving_avg_data[i] = moving_avg_data[i]/float(avg_iterations)
		    #print size
		    freq_resolution = samp_rate/size
		    p = m.center_freq - freq_resolution*((size/2)-1)
		    sensed_freq = [0]*size
		    for i in range(0,size/2):
			    sensed_freq[i]= p
			    #print p, '\t', moving_avg_data[i+(size/2)]
			    p=p+freq_resolution
		    
		    for i in range(0,size/2):
			    sensed_freq[i+(size/2)]= p
			    #print p, '\t',  moving_avg_data[i]
			    p=p+freq_resolution
			    
		    avg_data = [0]*(size)
		    for i in range(0,size/2):
			    avg_data[i] = moving_avg_data[i+(size/2)]
			    avg_data[i+(size/2)] = moving_avg_data[i]
			    
		    n = 0
		    power_temp = 10
		    for i in range(200,size-217):
			power = 0                      
			for j in range(0,17):
			    power = power + avg_data[i+j]
			#print sensed_freq[i+3],'\t', power
			if power < power_temp:
			    power_temp = power
			    index = i+8
		    center_freq = 1e5*math.ceil(sensed_freq[index]/1e5)
		    print 'Frequency=', center_freq
            startOpenBTS(center_freq)
            
		    
def startOpenBTS(frequency):            
    
    arfcn=int((frequency-935e6)/2e5)
    print 'ARFCN=', arfcn
    #DB modifications
    t=(arfcn,)
    conn=sqlite3.connect("/etc/OpenBTS/OpenBTS.db")
    cursor=conn.cursor()
    cursor.execute("update config set valuestring=? where keystring='GSM.Radio.C0'",t)
    conn.commit()
    #start the OpenBTS
    f=os.popen('~/ddp-stage-1-and-openbts/runOpenBTS.sh')
    f.close()
    
    
if __name__ == '__main__':
    t = ThreadClass()
    t.start()
    tb = my_top_block()
    
    try:
        main_loop(tb)

    except KeyboardInterrupt:
        pass
