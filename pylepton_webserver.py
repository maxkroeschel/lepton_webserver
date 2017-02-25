#!/usr/bin/env python

# Webserver imports
import Image
import threading
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from SocketServer import ThreadingMixIn
import StringIO

# PyLepton imports
import time
import picamera
import numpy as np
import cv2
import traceback
from pylepton.Lepton3 import Lepton3

# This is the webserver handler
class CamHandler(BaseHTTPRequestHandler):
	# Init stuff for PyLepton
	a = np.zeros((240, 320, 3), dtype=np.uint8)
	lepton_buf = np.zeros((120, 160, 1), dtype=np.uint16)
	img = picamera.PiCamera().add_overlay(np.getbuffer(a), size=(320,240), layer=3, alpha=int(128), crop=(0,0,160,120), vflip=flip_v)
	last_nr = 0

	def do_GET(self):
		if self.path.endswith('.mjpg'):
			self.send_response(200)
			self.send_header('Content-type','multipart/x-mixed-replace; boundary=--jpgboundary')
			self.end_headers()
			
			# This is the main handler, runs forever			
			while True:
				try:
					# PyLepton part
					_,nr = Lepton3("/dev/spidev0.0").capture(lepton_buf)
					if nr == last_nr:
						continue
					last_nr = nr
					cv2.normalize(lepton_buf, lepton_buf, 0, 65535, cv2.NORM_MINMAX)
					np.right_shift(lepton_buf, 8, lepton_buf)
					a[:lepton_buf.shape[0], :lepton_buf.shape[1], :] = lepton_buf
					img.update(np.getbuffer(a))
					
					# Webserver part
					jpg = Image.fromarray(img)
					tmpFile = StringIO.StringIO()
					jpg.save(tmpFile,'JPEG')
					self.wfile.write("--jpgboundary")
					self.send_header('Content-type','image/jpeg')
					self.send_header('Content-length',str(tmpFile.len))
					self.end_headers()
					jpg.save(self.wfile,'JPEG')
					time.sleep(0.05)
					
				except Exception:
					traceback.print_exc()
					
				finally:
					picamera.PiCamera().remove_overlay(img)
			return
			
		if self.path.endswith('.html'):
			self.send_response(200)
			self.send_header('Content-type','text/html')
			self.end_headers()
			self.wfile.write('<html><head></head><body>')
			self.wfile.write('<img src="http://127.0.0.1:8080/cam.mjpg"/>')
			self.wfile.write('</body></html>')
			return

# Main entry point
def main():
	# Init PiCamera
	picamera.PiCamera().resolution = (640, 480)
	picamera.PiCamera().framerate = 24
	picamera.PiCamera().vflip = False
	picamera.PiCamera().start_preview()
	picamera.PiCamera().fullscreen = True
	
	# Init Server
	try:
		time.sleep(0.2)
		# This is a reference to the CamHandler class
		server = ThreadedHTTPServer(('localhost', 8080), CamHandler)
		print "server started"
		server.serve_forever()
		
	except KeyboardInterrupt:
		server.socket.close()

if __name__ == '__main__':
	main()
