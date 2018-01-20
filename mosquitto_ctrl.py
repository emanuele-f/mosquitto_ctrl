#!/usr/bin/env python3

from multiprocessing import Process, Value
import subprocess
import select
import signal, os
import datetime
import time
import mqtt_cfg

##############################################################

MQTT_POWER_TOPIC="home/sonoff/switch/1/power"
MQTT_STATUS_TOPIC="home/sonoff/switch/1/power/stat"

AUTO_POWER_OFF_TIME="08:00"
AUTO_POWER_OFF_ENABLED=True
POWERSAVE_TURN_OFF_AFTER_MINUTES=40
POWERSAVE_TURN_ON_AFTER_MINUTES=20

##############################################################

def subscriber_job(status_v, shutting_down):
  cmd = ['mosquitto_sub', '-t', MQTT_STATUS_TOPIC, "-u", mqtt_cfg.username, "-P", mqtt_cfg.password]
  proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
  poll_obj = select.poll()
  poll_obj.register(proc.stdout, select.POLLIN)

  while not shutting_down.value:
    poll_result = poll_obj.poll(0)

    if poll_result:
      value = proc.stdout.readline().strip()
      #print(value)
      if value == b"on":
        status_v.value = 1
      else:
        status_v.value = 0
    else:
      time.sleep(3)

  # NOTE: term does not seem to stop it
  os.killpg(os.getpgid(proc.pid), signal.SIGKILL)

status_v = Value("i", -1)
shutting_down = Value("i", 0)

signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.signal(signal.SIGTERM, signal.SIG_IGN)
signal.signal(signal.SIGINT, signal.SIG_IGN)

subscriber_process = Process(target=subscriber_job, args=(status_v, shutting_down))
subscriber_process.start()

def handler(signum, frame):
  if not shutting_down.value:
    print("Terminating...")
    shutting_down.value = 1
  else:
    print("Exit now")
    exit(1)

signal.signal(signal.SIGHUP, handler)
signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)

next_change = None
auto_power_off_time = None
powersave_time = None
managed_status = None
powersave_running = False

def turn_cmd(on_off):
  global managed_status
  print("CMD " + on_off)

  cmd = ['mosquitto_pub', '-t', MQTT_POWER_TOPIC, "-u", mqtt_cfg.username, "-P", mqtt_cfg.password, "-m", on_off]
  subprocess.call(cmd)

  if on_off == "on":
    managed_status = 1
  else:
    managed_status = 0

def setNextPowerOff():
  global AUTO_POWER_OFF_ENABLED
  global AUTO_POWER_OFF_TIME
  global auto_power_off_time

  if AUTO_POWER_OFF_ENABLED:
    minutes, seconds = AUTO_POWER_OFF_TIME.split(":")
    now = datetime.datetime.fromtimestamp(time.time())
    next_off = now.replace(hour=int(minutes), minute=int(seconds), second=0)

    if next_off < datetime.datetime.now():
      next_off = next_off + datetime.timedelta(days=1)

    auto_power_off_time = time.mktime(next_off.timetuple())

setNextPowerOff()

while not shutting_down.value:
  now = time.time()

  if status_v.value == -1:
    # Waiting for first sync
    pass
  elif managed_status == None:
    # first sync
    managed_status = status_v.value
    is_on = status_v.value == 1

    if is_on:
      powersave_running = True
      powersave_time = now + POWERSAVE_TURN_OFF_AFTER_MINUTES * 60
      print("Status: ON")
    else:
      print("Status: OFF")
  elif auto_power_off_time and now >= auto_power_off_time:
    print("Automatic power off: " + AUTO_POWER_OFF_TIME)
    powersave_running = False
    turn_cmd("off")
    setNextPowerOff()
  else:
    value = status_v.value
    is_on = value == 1
    #print(value)
    #print(managed_status)

    if value != managed_status:
      # User change took place
      if not is_on:
        powersave_running = False
        print("User switched off")
      else:
        # restart timer
        powersave_running = True
        powersave_time = now + POWERSAVE_TURN_OFF_AFTER_MINUTES * 60
        print("User switched on")

      managed_status = value
    elif powersave_running and now >= powersave_time:
      if is_on:
        turn_cmd("off")
        powersave_time = now + POWERSAVE_TURN_ON_AFTER_MINUTES * 60
      else:
        turn_cmd("on")
        powersave_time = now + POWERSAVE_TURN_OFF_AFTER_MINUTES * 60

  time.sleep(5)
