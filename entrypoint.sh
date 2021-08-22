#!/bin/sh
#
# GaW-Vertretungsplan
# Copyright (C) 2019-2021  Florian Rädiker
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

cd /app
mkdir /static
cp -r /app/assets/static/* /static
find /static -mindepth 1 -mtime +1 -delete
python3 server.py
