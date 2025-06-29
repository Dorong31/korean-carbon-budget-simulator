from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import os
from datetime import datetime
import math

app = Flask(__name__, static_folder='static') 