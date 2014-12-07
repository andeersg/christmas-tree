from flask import Flask, render_template, request
import datetime, json, time, requests, yaml
import array, fcntl, time, signal, sys, random, re
app = Flask(__name__)

spi = file("/dev/spidev0.0", "wb")
fcntl.ioctl(spi, 0x40046b04, array.array('L', [400000]))

# Message Class
class Message:
  def __init__(self, direction, sender, points):
    stream = open(".settings", 'r')
    self.settings = yaml.load(stream)

    self.message = '<table><tr><td>' + self.senderAvatar(sender) + '</td><td>' + self.getRandomText(direction) % {'author': self.senderName(sender), 'number': points} + '</td></tr></table>'

    self.send()

  def getRandomText(self, direction):
    if direction == 'plus':
      self.color = 'green'
      return random.choice(self.settings[direction])
    elif direction == 'minus':
      self.color = 'red'
      return random.choice(self.settings[direction])
    else:
      return 'Unknown text'

  def senderName(self, sender):
    return '<a href="' + sender['html_url'] + '">' + sender['login'] + '</a>'

  def senderAvatar(self, sender):
    return '<img src="' + sender['avatar_url'] + '" width="48" height="48" Hspace="2" Vspace="2" />'

  def send(self):
    host = 'https://api.hipchat.com'
    path = '/v1/rooms/message'
    headers = { 'Content-type': 'application/x-www-form-urlencoded', 'User-Agent': 'RaspberryPi' }
    data = { 'room_id': self.settings['room_id'], 'from': self.settings['author'], 'message': self.message, 'message_format': 'html', 'color': self.color, 'format': 'json', 'auth_token': self.settings['hipchat_secret'] }
    r = requests.post(host + path, data=data, headers=headers)

# Christmas Tree class
class ChristmasTree:
  value = 0;
  settings = [];

  def __init__(self):
    self.value = 0;
    stream = open(".settings", 'r')
    self.settings = yaml.load(stream)

  def getValue(self):
    return self.value

  def plus(self, number):
    self.value += number
    if self.value >= len(self.settings['steps']):
      self.value = len(self.settings['steps']) - 1
    self.set()

  def minus(self, number):
    self.value -= number
    if self.value < 0:
      self.value = 0
    self.set()

  def set(self):
    for i in range(0, self.settings['num_leds']):
      try:
        self.writeLed(self.settings['steps'][self.value][i])
      except:
        self.writeLed({'r': 0, 'g': 0, 'b': 0})

    spi.flush()

  def writeLed(self, color):
    rgb = bytearray(3)
    rgb[0] = color['r']
    rgb[1] = color['g']
    rgb[2] = color['b']
    spi.write(rgb)


def push(response):
  branch = response['ref']
  if branch.startswith('refs/heads/'):
    branch = re.sub('refs/heads/', '', branch);
  master_branch = response['repository']['master_branch']
  sender = response['sender']
  points = len(response['commits'])

  # do something
  if branch == master_branch:
    GITree.minus(points)
    Message('minus', sender, points)
  else:
    GITree.plus(points)
    Message('plus', sender, points)

def create(sender):
  GITree.plus(2)
  Message('plus', sender, 2)

def pull_request(sender):
  GITree.plus(2)
  Message('plus', sender, 2)


# define new Christmas tree object
GITree = ChristmasTree()

@app.route("/", methods=['GET'])
def index():
  return render_template('index.html')

@app.route("/endpoint", methods=['GET', 'POST'])
def endpoint():
  if request.headers.get('X-GitHub-Event') is None:
    return "X-Github-Event header required", 400;

  event = request.headers.get('X-GitHub-Event')

  # Get JSON from input.
  response = request.get_json()
  if event == "push":
    push(response)
  elif event == "create":
    create(response['sender'])
  elif event == "pull_request":
    pull_request(response['sender'])
  else:
    return 'This event is not yet supported', 200

  return 'ok', 200

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=80, debug=True)
