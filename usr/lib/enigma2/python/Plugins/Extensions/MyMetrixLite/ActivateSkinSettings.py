# -*- coding: utf-8 -*-
from __future__ import division
#######################################################################
#
#    MyMetrixLite by arn354 & svox
#    based on
#    MyMetrix
#    Coded by iMaxxx (c) 2013
#
#
#  This plugin is licensed under the Creative Commons
#  Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#  To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/
#  or send a letter to Creative Commons, 559 Nathan Abbott Way, Stanford, California 94305, USA.
#
#  This plugin is NOT free software. It is open source, you are allowed to
#  modify it (if you keep the license), but it may not be commercially
#  distributed other than under the conditions noted above.
#
#
#######################################################################

from datetime import datetime
from math import floor, sqrt
from os import remove, statvfs, listdir, system, mkdir, unlink, symlink, rename
from os.path import exists, getsize, isdir, isfile, islink, join as pathjoin, realpath
from re import sub, match, findall
from shutil import move, copy, rmtree
from subprocess import getoutput
from time import time

from PIL import Image, ImageFont, ImageDraw

from Components.config import config, configfile
from Components.NimManager import nimmanager

from enigma import getDesktop
from Components.SystemInfo import BoxInfo
from skin import colors, reloadWindowStyles, parseColor

from . import _, initColorsConfig, initWeatherConfig, initOtherConfig, initFontsConfig, appendSkinFile, \
	SKIN_SOURCE, SKIN_TARGET, SKIN_TARGET_TMP, \
	SKIN_TEMPLATES_SOURCE, SKIN_TEMPLATES_TARGET, SKIN_TEMPLATES_TARGET_TMP, \
	SKIN_INFOBAR_SOURCE, SKIN_INFOBAR_TARGET, SKIN_INFOBAR_TARGET_TMP, \
	SKIN_SECOND_INFOBAR_SOURCE, SKIN_SECOND_INFOBAR_TARGET, SKIN_SECOND_INFOBAR_TARGET_TMP, \
	SKIN_SECOND_INFOBAR_ECM_SOURCE, SKIN_SECOND_INFOBAR_ECM_TARGET, SKIN_SECOND_INFOBAR_ECM_TARGET_TMP, \
	SKIN_INFOBAR_LITE_SOURCE, SKIN_INFOBAR_LITE_TARGET, SKIN_INFOBAR_LITE_TARGET_TMP, \
	SKIN_CHANNEL_SELECTION_SOURCE, SKIN_CHANNEL_SELECTION_TARGET, SKIN_CHANNEL_SELECTION_TARGET_TMP, \
	SKIN_MOVIEPLAYER_SOURCE, SKIN_MOVIEPLAYER_TARGET, SKIN_MOVIEPLAYER_TARGET_TMP, \
	SKIN_EMC_SOURCE, SKIN_EMC_TARGET, SKIN_EMC_TARGET_TMP, \
	SKIN_OPENATV_SOURCE, SKIN_OPENATV_TARGET, SKIN_OPENATV_TARGET_TMP, \
	SKIN_PLUGINS_SOURCE, SKIN_PLUGINS_TARGET, SKIN_PLUGINS_TARGET_TMP, \
	SKIN_UNCHECKED_SOURCE, SKIN_UNCHECKED_TARGET, SKIN_UNCHECKED_TARGET_TMP, \
	SKIN_DESIGN_SOURCE, SKIN_DESIGN_TARGET, SKIN_DESIGN_TARGET_TMP


#############################################################


def round_half_up(n, decimals=0):
	multiplier = 10 ** decimals
	return floor(n * multiplier + 0.5) / multiplier


class ActivateSkinSettings:

	def __init__(self):
		self.ErrorCode = None
		self.ButtonEffect = None

	def WriteSkin(self, silent=False):
		#silent = True  -> returned int value for defined error code
		#silent = False -> tuple returned -> ident, message

		#error codes for silent mode
		#(called from SystemPlugins/SoftwareManager/BackupRestore.py after restore settings and from skin.py after flash a new image (fast restore function))
		#0:"No Error"
		#1:"Unknown Error creating Skin. Please check after reboot MyMetrixLite-Plugin and apply your settings."
		#2:"Error creating HD-Skin. Not enough flash memory free."
		#3:"Error creating EHD-Skin. Not enough flash memory free. Using HD-Skin!"
		#4:"Error creating EHD-Skin. Icon package download not available. Using HD-Skin!"
		#5:"Error creating EHD-Skin. Using HD-Skin!"
		#6:"Error creating EHD-Skin. Some EHD-Icons are missing. Using HD-Skin!"
		#7:"Error, unknown Result!"

		self.silent = silent
		if self.silent:
			self.E2settings = open("/etc/enigma2/settings", "r").read()
			if config.skin.primary_skin.value != "MetrixHD/skin.MySkin.xml" and 'config.skin.primary_skin=MetrixHD/skin.MySkin.xml' not in self.E2settings:
				print('MetrixHD is not the primary skin or runs with default settings. No restore action needed!')
				return 0
			from Components.PluginComponent import plugins  # need for fast restore in skin.py
		self.initConfigs()
		self.CheckSettings()
		if self.ErrorCode is None:
			if self.silent:
				self.ErrorCode = 7
			else:
				self.ErrorCode = 'unknown', _('Error, unknown Result!')
		return self.ErrorCode

	def initConfigs(self):
		initOtherConfig()
		initColorsConfig()
		initWeatherConfig()
		initFontsConfig()

	def RefreshIcons(self, restore=False):
		# called from SystemPlugins/SoftwareManager/plugin.py after software update and from Screens/SkinSelector.py after changing skin
		self.initConfigs()
		self.getEHDSettings()
		screenwidth = getDesktop(0).size().width()
		if screenwidth and screenwidth != 1280 or restore:
			if restore:
				self.EHDres = 'HD'
				print(f"[MetrixHD] restoring original {self.EHDres} icons after changing skin...")
			else:
				print(f"[MetrixHD] refreshing {self.EHDres} icons after software update...")
			self.updateIcons(self.EHDres)
			print("[MetrixHD] ...done.")

	def getEHDSettings(self, onlyCheck=False):
		tested = config.plugins.MyMetrixLiteOther.EHDtested.value.split('_|_')
		EHDtested = len(tested) == 2 and BoxInfo.getItem("machinebuild") in tested[0] and config.plugins.MyMetrixLiteOther.EHDenabled.value in tested[1]
		if config.plugins.MyMetrixLiteOther.EHDenabled.value == '0':
			self.EHDenabled = False
			self.EHDfactor = 1
			self.EHDres = 'HD'
			self.EHDtxt = 'Standard HD'
		elif config.plugins.MyMetrixLiteOther.EHDenabled.value == '1' and EHDtested:
			self.EHDenabled = True
			self.EHDfactor = 1.5
			self.EHDres = 'FHD'
			self.EHDtxt = 'Full HD'
		elif config.plugins.MyMetrixLiteOther.EHDenabled.value == '2' and EHDtested:
			self.EHDenabled = True
			self.EHDfactor = 3
			self.EHDres = 'UHD'
			self.EHDtxt = 'Ultra HD'
		else:
			self.EHDenabled = False
			self.EHDfactor = 1
			self.EHDres = 'HD'
			self.EHDtxt = 'Standard HD'
			if onlyCheck or not self.silent:
				self.ErrorCode = 'checkEHDsettings', _("Your enhanced hd settings are inconsistent. Please check this.")

	def CheckSettings(self, onlyCheck=False):
		#first check is ehd tested, ehd-settings and available ehd-icons
		self.getEHDSettings(onlyCheck)

		if self.EHDenabled:
			self.service_name = f'enigma2-plugin-skins-metrix-atv-{self.EHDres.lower()}-icons'
			return_value = getoutput("/usr/bin/opkg list-installed " + self.service_name)
			if self.service_name not in return_value:
				if onlyCheck or not self.silent:
					self.ErrorCode = 'checkEHDsettings', _("Your enhanced hd settings are inconsistent. Please check this.")
				elif self.silent:
					stat = statvfs("/usr/share/enigma2/MetrixHD/")
					freeflash = stat.f_bavail * stat.f_bsize / 1024 / 1024
					filesize = 10
					if self.EHDres == 'UHD':
						filesize = 25
					if freeflash < filesize:
						self.ErrorCode = 3
					else:
						system('/usr/bin/opkg update')
						ret = str(system('/usr/bin/opkg install ' + self.service_name))
						if 'Unknown package' in ret or "Collected errors" in ret:
							self.ErrorCode = 4
					if self.ErrorCode:
						self.EHDenabled = False
						self.EHDfactor = 1
						self.EHDres = 'HD'
						self.EHDtxt = 'Standard HD'

		if onlyCheck or self.ErrorCode:
			return self.ErrorCode
		self.applyChanges()

	def applyChanges(self):
		apply_starttime = time()
		print("MyMetrixLite apply Changes")

		try:
			# make backup of skin.xml
			bname = "_original_file_.xml"
			f = open(SKIN_SOURCE, 'r')
			firstline = f.readline()
			f.close()
			if '<!-- original file -->' in firstline:
				copy(SKIN_SOURCE, SKIN_SOURCE + bname)
			else:
				copy(SKIN_SOURCE + bname, SKIN_SOURCE)

			skinfiles = [(SKIN_SOURCE, SKIN_TARGET, SKIN_TARGET_TMP),
						(SKIN_TEMPLATES_SOURCE, SKIN_TEMPLATES_TARGET, SKIN_TEMPLATES_TARGET_TMP),
						(SKIN_INFOBAR_SOURCE, SKIN_INFOBAR_TARGET, SKIN_INFOBAR_TARGET_TMP),
						(SKIN_SECOND_INFOBAR_SOURCE, SKIN_SECOND_INFOBAR_TARGET, SKIN_SECOND_INFOBAR_TARGET_TMP),
						(SKIN_SECOND_INFOBAR_ECM_SOURCE, SKIN_SECOND_INFOBAR_ECM_TARGET, SKIN_SECOND_INFOBAR_ECM_TARGET_TMP),
						(SKIN_INFOBAR_LITE_SOURCE, SKIN_INFOBAR_LITE_TARGET, SKIN_INFOBAR_LITE_TARGET_TMP),
						(SKIN_CHANNEL_SELECTION_SOURCE, SKIN_CHANNEL_SELECTION_TARGET, SKIN_CHANNEL_SELECTION_TARGET_TMP),
						(SKIN_MOVIEPLAYER_SOURCE, SKIN_MOVIEPLAYER_TARGET, SKIN_MOVIEPLAYER_TARGET_TMP),
						(SKIN_EMC_SOURCE, SKIN_EMC_TARGET, SKIN_EMC_TARGET_TMP),
						(SKIN_OPENATV_SOURCE, SKIN_OPENATV_TARGET, SKIN_OPENATV_TARGET_TMP),
						(SKIN_PLUGINS_SOURCE, SKIN_PLUGINS_TARGET, SKIN_PLUGINS_TARGET_TMP),
						(SKIN_UNCHECKED_SOURCE, SKIN_UNCHECKED_TARGET, SKIN_UNCHECKED_TARGET_TMP),
						(SKIN_DESIGN_SOURCE, SKIN_DESIGN_TARGET, SKIN_DESIGN_TARGET_TMP)]
			buttons = [
						('info.png', _('INFO')),
						('key_audio.png', _('AUDIO')),
						('key_av.png', _('AV')),
						('key_bouquet.png', _('BOUQUET')),
						('key_end.png', _('END')),
						('key_epg.png', _('EPG')),
						('key_exit.png', _('EXIT')),
						('key_help.png', _('HELP')),
						('key_home.png', _('HOME')),
						('key_leftright.png', _('< >')),
						('key_tv.png', _('TV')),
						('key_updown.png', _('< >')),
						('menu.png', _('MENU')),
						('ok.png', _('OK')),
						('text.png', _('TEXT'))
						]
			buttonpath = {'HD': '/usr/share/enigma2/MetrixHD/buttons/', 'FHD': '/usr/share/enigma2/MetrixHD/FHD/buttons/', 'UHD': '/usr/share/enigma2/MetrixHD/UHD/buttons/'}

			################
			# check free flash for _TARGET and _TMP files
			################

			stat = statvfs("/usr/share/enigma2/MetrixHD/")
			freeflash = stat.f_bavail * stat.f_bsize / 1024

			filesize = 0
			for file in skinfiles:
				if exists(file[1]):
					filesize += getsize(file[1])
				else:
					if exists(file[0]):
						filesize += getsize(file[0]) * 2

			reserve = 256
			filesize = filesize / 1024 + reserve

			if freeflash < filesize:
				self.ErrorCode = 2
				if not self.silent:
					self.ErrorCode = 'ErrorCode_2', _("Not enough free flash memory to create the new %s skin files. ( %d kb is required )") % (self.EHDtxt, filesize)
				return

			################
			# InfoBar
			################

			infobarSkinSearchAndReplace = []

			if config.plugins.MyMetrixLiteOther.showTunerinfo.getValue() is True:
				if config.plugins.MyMetrixLiteOther.setTunerAuto.getValue() is False:
					infobarSkinSearchAndReplace.append(['<panel name="INFOBARTUNERINFO-X" />', f'<panel name="INFOBARTUNERINFO-{config.plugins.MyMetrixLiteOther.setTunerManual.getValue()}" />'])
				#else:
				#    infobarSkinSearchAndReplace.append(['<panel name="INFOBARTUNERINFO-X" />', '<panel name="INFOBARTUNERINFO-%d" />' % self.getTunerCount()])
			else:
				infobarSkinSearchAndReplace.append(['<panel name="INFOBARTUNERINFO-X" />', ''])

			if config.plugins.MyMetrixLiteOther.showInfoBarClock.getValue() is False:
				infobarSkinSearchAndReplace.append(['<panel name="CLOCKWIDGET" />', ''])

			if config.plugins.MyMetrixLiteOther.showInfoBarServiceIcons.getValue() is False:
				infobarSkinSearchAndReplace.append(['<panel name="INFOBARSERVICEINFO" />', ''])

			if config.plugins.MyMetrixLiteOther.showRecordstate.getValue() is False:
				infobarSkinSearchAndReplace.append(['<panel name="INFOBARRECORDSTATE" />', ''])

			if config.plugins.MyMetrixLiteOther.showSnr.getValue() is False:
				infobarSkinSearchAndReplace.append(['<panel name="INFOBARSNR" />', ''])
			else:
				if (config.plugins.MyMetrixLiteOther.showOrbitalposition.getValue() and config.plugins.MyMetrixLiteOther.showInfoBarResolution.getValue() and config.plugins.MyMetrixLiteOther.showInfoBarResolutionExtended.getValue()) is True:
					infobarSkinSearchAndReplace.append(['<panel name="INFOBARSNR" />', '<panel name="INFOBARSNR-2" />'])

			if config.plugins.MyMetrixLiteOther.showOrbitalposition.getValue() is False:
				infobarSkinSearchAndReplace.append(['<panel name="INFOBARORBITALPOSITION" />', ''])
			else:
				if (config.plugins.MyMetrixLiteOther.showInfoBarResolution.getValue() and config.plugins.MyMetrixLiteOther.showInfoBarResolutionExtended.getValue()) is True:
					infobarSkinSearchAndReplace.append(['<panel name="INFOBARORBITALPOSITION" />', '<panel name="INFOBARORBITALPOSITION-2" />'])

			if config.plugins.MyMetrixLiteOther.showInfoBarResolution.getValue() is False:
				infobarSkinSearchAndReplace.append(['<panel name="INFOBARRESOLUTION" />', ''])
			else:
				if config.plugins.MyMetrixLiteOther.showInfoBarResolutionExtended.getValue() is True:
					infobarSkinSearchAndReplace.append(['<panel name="INFOBARRESOLUTION" />', '<panel name="INFOBARRESOLUTION-2" />'])

			if config.plugins.MyMetrixLiteOther.showSTBinfo.getValue() is True:
				infobarSkinSearchAndReplace.append(['<!--panel name="STBINFO" /-->', '<panel name="STBINFO" />'])

			channelNameXML = self.getChannelNameXML(
				"30,455",
				config.plugins.MyMetrixLiteOther.infoBarChannelNameFontSize.getValue(),
				config.plugins.MyMetrixLiteOther.showChannelNumber.getValue(),
				config.plugins.MyMetrixLiteOther.showChannelName.getValue()
			)
			infobarSkinSearchAndReplace.append(['<panel name="CHANNELNAME" />', channelNameXML])

			# SecondInfoBar
			skin_lines = appendSkinFile(SKIN_SECOND_INFOBAR_SOURCE, infobarSkinSearchAndReplace)

			xFile = open(SKIN_SECOND_INFOBAR_TARGET_TMP, "w")
			for xx in skin_lines:
				xFile.writelines(xx)
			xFile.close()

			# InfoBar
			if config.plugins.MyMetrixLiteOther.showExtendedinfo.getValue() is True:
				infobarSkinSearchAndReplace.append(['<!--panel name="INFOBAREXTENDEDINFO" /-->', '<panel name="INFOBAREXTENDEDINFO" />'])

			skin_lines = appendSkinFile(SKIN_INFOBAR_SOURCE, infobarSkinSearchAndReplace)

			xFile = open(SKIN_INFOBAR_TARGET_TMP, "w")
			for xx in skin_lines:
				xFile.writelines(xx)
			xFile.close()

			################
			# ChannelSelection
			################

			channelSelectionSkinSearchAndReplace = []

			primetime = ""
			if int(config.plugins.MyMetrixLiteOther.SkinDesign.value) > 1 and (config.plugins.MyMetrixLiteOther.channelSelectionStyle.value == "CHANNELSELECTION-1" or config.plugins.MyMetrixLiteOther.channelSelectionStyle.value == "CHANNELSELECTION-2") and config.plugins.MyMetrixLiteOther.channelSelectionShowPrimeTime.value:
				primetime = "P"
			channelSelectionSkinSearchAndReplace.append(['<panel name="CHANNELSELECTION-1" />', f'<panel name="{config.plugins.MyMetrixLiteOther.channelSelectionStyle.getValue()}{primetime}" />'])

			skin_lines = appendSkinFile(SKIN_CHANNEL_SELECTION_SOURCE, channelSelectionSkinSearchAndReplace)

			xFile = open(SKIN_CHANNEL_SELECTION_TARGET_TMP, "w")
			for xx in skin_lines:
				xFile.writelines(xx)
			xFile.close()

			################
			# MoviePlayer
			################

			moviePlayerSkinSearchAndReplace = []

			if config.plugins.MyMetrixLiteOther.showSTBinfoMoviePlayer.getValue() is True:
				if config.plugins.MyMetrixLiteOther.InfoBarMoviePlayerDesign.getValue() == "1":
					moviePlayerSkinSearchAndReplace.append(['<!--panel name="STBINFOMOVIEPLAYER" /-->', '<panel name="STBINFOMOVIEPLAYER" />'])
				else:
					moviePlayerSkinSearchAndReplace.append(['<!--panel name="STBINFO" /-->', '<panel name="STBINFO" />'])

			if config.plugins.MyMetrixLiteOther.showInfoBarClockMoviePlayer.getValue() is False:
				moviePlayerSkinSearchAndReplace.append(['<panel name="CLOCKWIDGET" />', ''])

			namepos = "30,465"
			if config.plugins.MyMetrixLiteOther.InfoBarMoviePlayerDesign.getValue() == "2":
				if config.plugins.MyMetrixLiteOther.showMoviePlayerResolutionExtended.getValue() is True:
					moviePlayerSkinSearchAndReplace.append(['<panel name="RESOLUTIONMOVIEPLAYER" />', '<panel name="RESOLUTIONMOVIEPLAYER-2" />'])
			else:
				moviePlayerSkinSearchAndReplace.append(['<panel name="MoviePlayer_2" />', f'<panel name="MoviePlayer_{config.plugins.MyMetrixLiteOther.InfoBarMoviePlayerDesign.value}" />'])
				if config.plugins.MyMetrixLiteOther.InfoBarMoviePlayerDesign.getValue() == "3":
					namepos = "30,535"

			channelNameXML = self.getChannelNameXML(
				namepos,
				config.plugins.MyMetrixLiteOther.infoBarChannelNameFontSize.getValue(),
				#config.plugins.MyMetrixLiteOther.showChannelNumber.getValue(),
				False,
				config.plugins.MyMetrixLiteOther.showMovieName.getValue()
			)
			moviePlayerSkinSearchAndReplace.append(['<panel name="MOVIENAME" />', channelNameXML])

			if config.plugins.MyMetrixLiteOther.showMovieTime.getValue() == "2":
				moviePlayerSkinSearchAndReplace.append(['<panel name="MoviePlayer_2_time" />', '<panel name="MoviePlayer_' + config.plugins.MyMetrixLiteOther.InfoBarMoviePlayerDesign.getValue() + '_time" />'])
			else:
				moviePlayerSkinSearchAndReplace.append(['<panel name="MoviePlayer_2_time" />', ''])

			if config.plugins.MyMetrixLiteOther.showMovieListScrollbar.value:
				moviePlayerSkinSearchAndReplace.append(['scrollbarMode="showNever"', 'scrollbarMode="showOnDemand"'])

			if config.plugins.MyMetrixLiteOther.showMovieListRunningtext.value:
				delay = str(config.plugins.MyMetrixLiteOther.runningTextStartdelay.value)
				speed = str(config.plugins.MyMetrixLiteOther.runningTextSpeed.value)
				moviePlayerSkinSearchAndReplace.append(['movetype=none,startdelay=600,steptime=60', f'movetype=running,startdelay={delay},steptime={speed}'])

			if config.plugins.MyMetrixLiteOther.movielistStyle.value == 'right':
				moviePlayerSkinSearchAndReplace.append(['<panel name="MovieSelection_left"/>', '<panel name="MovieSelection_right"/>'])

			skin_lines = appendSkinFile(SKIN_MOVIEPLAYER_SOURCE, moviePlayerSkinSearchAndReplace)

			xFile = open(SKIN_MOVIEPLAYER_TARGET_TMP, "w")
			for xx in skin_lines:
				xFile.writelines(xx)
			xFile.close()

			################
			# EMC
			################

			EMCSkinSearchAndReplace = []

			if config.plugins.MyMetrixLiteOther.showSTBinfoMoviePlayer.getValue() is True:
				if config.plugins.MyMetrixLiteOther.InfoBarMoviePlayerDesign.getValue() == "1":
					EMCSkinSearchAndReplace.append(['<!--panel name="STBINFOMOVIEPLAYER" /-->', '<panel name="STBINFOMOVIEPLAYER" />'])
				else:
					EMCSkinSearchAndReplace.append(['<!--panel name="STBINFO" /-->', '<panel name="STBINFO" />'])

			if config.plugins.MyMetrixLiteOther.showInfoBarClockMoviePlayer.getValue() is False:
				EMCSkinSearchAndReplace.append(['<panel name="CLOCKWIDGET" />', ''])

			if config.plugins.MyMetrixLiteOther.showEMCMediaCenterCover.getValue() == "small":
				if config.plugins.MyMetrixLiteOther.showEMCMediaCenterCoverInfobar.getValue() is True and config.plugins.MyMetrixLiteOther.InfoBarMoviePlayerDesign.getValue() == "2":
					if config.plugins.MyMetrixLiteOther.showMovieName.value:
						EMCSkinSearchAndReplace.append(['<panel name="EMCMediaCenterCover_no" />', '<panel name="EMCMediaCenterCover_small_infobar" />'])
					else:
						EMCSkinSearchAndReplace.append(['<panel name="EMCMediaCenterCover_no" />', '<panel name="EMCMediaCenterCover_large_infobar" />'])
				else:
					EMCSkinSearchAndReplace.append(['<panel name="EMCMediaCenterCover_no" />', '<panel name="EMCMediaCenterCover_small" />'])
			elif config.plugins.MyMetrixLiteOther.showEMCMediaCenterCover.getValue() == "large":
				EMCSkinSearchAndReplace.append(['<panel name="EMCMediaCenterCover_no" />', '<panel name="EMCMediaCenterCover_large" />'])

			if config.plugins.MyMetrixLiteOther.showEMCSelectionCover.getValue() == "small":
				EMCSkinSearchAndReplace.append(['<panel name="EMCSelectionCover_no" />', '<panel name="EMCSelectionCover_small" />'])
			elif config.plugins.MyMetrixLiteOther.showEMCSelectionCover.getValue() == "large":
				EMCSkinSearchAndReplace.append(['<panel name="EMCSelectionCover_no" />', '<panel name="EMCSelectionCover_large" />'])
			if config.plugins.MyMetrixLiteOther.showEMCSelectionCoverLargeDescription.getValue() is False:
					EMCSkinSearchAndReplace.append(['<panel name="EMCSelectionCover_large_description_on" />', '<panel name="EMCSelectionCover_large_description_off" />'])

			posNR = config.plugins.MyMetrixLiteOther.showEMCSelectionPicon.value == 'right'
			progress = False
			if not self.silent:
				try:
					config.EMC.skin_able.setValue(True)
					config.EMC.use_orig_skin.setValue(False)
					config.EMC.movie_cover.setValue(config.plugins.MyMetrixLiteOther.showEMCSelectionCover.value != 'no')
					config.EMC.movie_picons.setValue(config.plugins.MyMetrixLiteOther.showEMCSelectionPicon.value != 'no')
					config.EMC.save()
					progress = 'P' in config.EMC.movie_progress.value
				except Exception:
					print("Error: find emc config - it's not installed ?")
			else:
				progress = "config.EMC.movie_progress=P" in self.E2settings or "config.EMC.movie_progress=" not in self.E2settings

			sizeW = 700
			sizeH = 480
			gap = 5
			margin = 2
			scale = config.plugins.MyMetrixLiteFonts.epgtext_scale.value / 95.0  # 95% standard scale
			if config.plugins.MyMetrixLiteOther.showMovieListScrollbar.value:
				sizeW -= margin + config.plugins.MyMetrixLiteOther.SkinDesignScrollbarSliderWidth.value + config.plugins.MyMetrixLiteOther.SkinDesignScrollbarBorderWidth.value * 2  # place for scrollbar
				EMCSkinSearchAndReplace.append(['scrollbarMode="showNever"', 'scrollbarMode="showOnDemand"'])

			if config.plugins.MyMetrixLiteOther.showEMCSelectionRows.value == "+8":
				itemHeight = 20
				rowfactor = itemHeight / 30.0
				offsetHicon = 0
				offsetPosIcon = 6
				offsetHbar = -2
			elif config.plugins.MyMetrixLiteOther.showEMCSelectionRows.value == "+6":
				sizeH = 484
				itemHeight = 22
				rowfactor = itemHeight / 30.0
				offsetHicon = 0
				offsetPosIcon = 4
				offsetHbar = -2
			elif config.plugins.MyMetrixLiteOther.showEMCSelectionRows.value == "+4":
				itemHeight = 24
				rowfactor = itemHeight / 30.0
				offsetHicon = 0
				offsetPosIcon = 2
				offsetHbar = -2
			elif config.plugins.MyMetrixLiteOther.showEMCSelectionRows.value == "+2":
				sizeH = 486
				itemHeight = 27
				rowfactor = itemHeight / 30.0
				offsetPosIcon = 0
				offsetHicon = 1
				offsetHbar = -1
			elif config.plugins.MyMetrixLiteOther.showEMCSelectionRows.value == "-2":
				sizeH = 476
				itemHeight = 34
				rowfactor = itemHeight / 30.0
				offsetHicon = 1
				offsetPosIcon = 0
				offsetHbar = 1
			elif config.plugins.MyMetrixLiteOther.showEMCSelectionRows.value == "-4":
				itemHeight = 40
				rowfactor = itemHeight / 30.0
				offsetPosIcon = 0
				offsetHicon = 3
				offsetHbar = 4
			else:
				itemHeight = 30
				rowfactor = 1
				offsetPosIcon = 0
				offsetHicon = 0
				offsetHbar = 0

			#font
			CoolFont = int(20 * rowfactor)
			CoolSelectFont = int(20 * rowfactor)
			CoolDateFont = int(20 * rowfactor)
			#height
			CoolBarSizeV = int(10 * rowfactor)
			CoolPiconHPos = 2
			CoolPiconHeight = itemHeight - CoolPiconHPos * 2
			CoolIconHPos = 2 + offsetHicon
			CoolBarHPos = 12 + offsetHbar
			CoolMovieHPos = 2 + offsetHicon
			CoolDateHPos = 2 + offsetHicon
			CoolProgressHPos = 2 + offsetHicon
			#width
			if progress:
				CoolBarSizeH = int(config.plugins.MyMetrixLiteOther.setEMCbarsize.value)
			else:
				CoolBarSizeH = 0
			CoolDateWidth = int(int(config.plugins.MyMetrixLiteOther.setEMCdatesize.value) * scale * rowfactor)
			CoolPiconWidth = int(CoolPiconHeight * 1.73)
			CoolCSDirInfoWidth = int(int(config.plugins.MyMetrixLiteOther.setEMCdirinfosize.value) * scale * rowfactor)
			CoolFolderSize = sizeW - CoolCSDirInfoWidth - gap - margin - 38  # 38 is progressbar position
			if not CoolCSDirInfoWidth:
				CoolFolderSize = sizeW - 35  # - margin
			CoolMoviePos = 38 + CoolBarSizeH + gap
			#if not CoolBarSizeH:
			#    CoolMoviePos = 38
			CoolMovieSize = sizeW - CoolDateWidth - CoolMoviePos - gap - margin
			if not CoolDateWidth:
				CoolMovieSize = sizeW - CoolMoviePos  # - margin
			CoolMoviePiconSize = CoolMovieSize - CoolPiconWidth - gap
			CoolDatePos = sizeW - CoolDateWidth - margin
			CoolCSPos = sizeW - CoolCSDirInfoWidth - margin
			CoolIconPos = 4 + offsetPosIcon

			EMCSkinSearchAndReplace.append(['size="700,480" itemHeight="30" CoolFont="epg_text;20" CoolSelectFont="epg_text;20" CoolDateFont="epg_text;20"', f'size="700,{sizeH}" itemHeight="{itemHeight}" CoolFont="epg_text;{CoolFont}" CoolSelectFont="epg_text;{CoolSelectFont}" CoolDateFont="epg_text;{CoolDateFont}"'])

			EMCSkinSearchAndReplace.append(['size="700,240" itemHeight="30" CoolFont="epg_text;20" CoolSelectFont="epg_text;20" CoolDateFont="epg_text;20"', f'size="700,{sizeH // 2}" itemHeight="{itemHeight}" CoolFont="epg_text;{CoolFont}" CoolSelectFont="epg_text;{CoolSelectFont}" CoolDateFont="epg_text;{CoolDateFont}"'])

			EMCSkinSearchAndReplace.append(['CoolProgressHPos="2" CoolIconPos="4" CoolIconHPos="2" CoolIconSize="26,26" CoolBarPos="35" CoolBarHPos="12" CoolBarSize="50,10" CoolBarSizeSa="50,10" CoolMoviePos="90"', f'CoolProgressHPos="{CoolProgressHPos}" CoolIconPos="{CoolIconPos}" CoolIconHPos="{CoolIconHPos}" CoolIconSize="26,26" CoolBarPos="35" CoolBarHPos="{CoolBarHPos}" CoolBarSize="{CoolBarSizeH},{CoolBarSizeV}" CoolBarSizeSa="{CoolBarSizeH},{CoolBarSizeV}" CoolMoviePos="{CoolMoviePos - margin}"'])

			CoolMoviePiconPos = CoolMoviePos + CoolPiconWidth + gap - margin
			CoolPiconPos = CoolMoviePos - margin
			EMCSkinSearchAndReplace.append(['CoolMovieHPos="2" CoolMovieSize="494" CoolFolderSize="475" CoolDatePos="592" CoolDateHPos="2" CoolDateWidth="104" CoolPiconPos="90" CoolPiconHPos="2" CoolPiconWidth="45" CoolPiconHeight="26" CoolMoviePiconPos="140" CoolMoviePiconSize="445" CoolCSWidth="140" CoolDirInfoWidth="140" CoolCSPos="555"', f'CoolMovieHPos="{CoolMovieHPos}" CoolMovieSize="{CoolMovieSize}" CoolFolderSize="{CoolFolderSize}" CoolDatePos="{CoolDatePos}" CoolDateHPos="{CoolDateHPos}" CoolDateWidth="{CoolDateWidth}" CoolPiconPos="{CoolPiconPos}" CoolPiconHPos="{CoolPiconHPos}" CoolPiconWidth="{CoolPiconWidth}" CoolPiconHeight="{CoolPiconHeight}" CoolMoviePiconPos="{CoolMoviePiconPos}" CoolMoviePiconSize="{CoolMoviePiconSize}" CoolCSWidth="{CoolCSDirInfoWidth}" CoolDirInfoWidth="{CoolCSDirInfoWidth}" CoolCSPos="{CoolCSPos}"'])

			CoolMoviePiconPos = CoolMoviePos - margin
			CoolPiconPos = CoolDatePos - CoolPiconWidth - gap - margin
			if not CoolDateWidth:
				CoolPiconPos = CoolDatePos - CoolPiconWidth
			EMCSkinSearchAndReplace.append(['CoolMovieHPos="2" CoolMovieSize="494" CoolFolderSize="475" CoolDatePos="592" CoolDateHPos="2" CoolDateWidth="104" CoolPiconPos="540" CoolPiconHPos="2" CoolPiconWidth="45" CoolPiconHeight="26" CoolMoviePiconPos="90" CoolMoviePiconSize="445" CoolCSWidth="140" CoolDirInfoWidth="140" CoolCSPos="555"', f'CoolMovieHPos="{CoolMovieHPos}" CoolMovieSize="{CoolMovieSize}" CoolFolderSize="{CoolFolderSize}" CoolDatePos="{CoolDatePos}" CoolDateHPos="{CoolDateHPos}" CoolDateWidth="{CoolDateWidth}" CoolPiconPos="{CoolPiconPos}" CoolPiconHPos="{CoolPiconHPos}" CoolPiconWidth="{CoolPiconWidth}" CoolPiconHeight="{CoolPiconHeight}" CoolMoviePiconPos="{CoolMoviePiconPos}" CoolMoviePiconSize="{CoolMoviePiconSize}" CoolCSWidth="{CoolCSDirInfoWidth}" CoolDirInfoWidth="{CoolCSDirInfoWidth}" CoolCSPos="{CoolCSPos}"'])

			if posNR:
				EMCSkinSearchAndReplace.append(['<panel name="EMCSelectionList_picon_left" />', '<panel name="EMCSelectionList_picon_right" />'])
				EMCSkinSearchAndReplace.append(['<panel name="EMCSelectionList_large_description_picon_left" />', '<panel name="EMCSelectionList_large_description_picon_right" />'])

			namepos = "30,465"
			if config.plugins.MyMetrixLiteOther.InfoBarMoviePlayerDesign.getValue() == "2":
				if config.plugins.MyMetrixLiteOther.showMoviePlayerResolutionExtended.getValue() is True:
					EMCSkinSearchAndReplace.append(['<panel name="RESOLUTIONMOVIEPLAYER" />', '<panel name="RESOLUTIONMOVIEPLAYER-2" />'])
			else:
				EMCSkinSearchAndReplace.append(['<panel name="EMCMediaCenter_2" />', f'<panel name="EMCMediaCenter_{config.plugins.MyMetrixLiteOther.InfoBarMoviePlayerDesign.value}" />'])
				if config.plugins.MyMetrixLiteOther.InfoBarMoviePlayerDesign.getValue() == "3":
					namepos = "30,535"

			channelNameXML = self.getChannelNameXML(
				namepos,
				config.plugins.MyMetrixLiteOther.infoBarChannelNameFontSize.getValue(),
				#config.plugins.MyMetrixLiteOther.showChannelNumber.getValue(),
				False,
				config.plugins.MyMetrixLiteOther.showMovieName.getValue()
			)
			EMCSkinSearchAndReplace.append(['<panel name="MOVIENAME" />', channelNameXML])

			if config.plugins.MyMetrixLiteOther.showMovieTime.getValue() == "2":
				EMCSkinSearchAndReplace.append(['<panel name="EMCMediaCenter_2_time" />', '<panel name="EMCMediaCenter_' + config.plugins.MyMetrixLiteOther.InfoBarMoviePlayerDesign.getValue() + '_time" />'])
			else:
				EMCSkinSearchAndReplace.append(['<panel name="EMCMediaCenter_2_time" />', ''])

			EMCSkinSearchAndReplace.append(['WatchingColor="#D8C100"', 'WatchingColor="#' + config.plugins.MyMetrixLiteColors.emcWatchingColor.value + '"'])
			EMCSkinSearchAndReplace.append(['FinishedColor="#5FA816"', 'FinishedColor="#' + config.plugins.MyMetrixLiteColors.emcFinishedColor.value + '"'])
			EMCSkinSearchAndReplace.append(['RecordingColor="#E51400"', 'RecordingColor="#' + config.plugins.MyMetrixLiteColors.emcRecordingColor.value + '"'])

			if config.plugins.MyMetrixLiteColors.emcCoolHighlightColor.getValue() is False:
				EMCSkinSearchAndReplace.append(['CoolHighlightColor="1"', 'CoolHighlightColor="0"'])

			if config.plugins.MyMetrixLiteOther.showMovieListRunningtext.value:
				delay = str(config.plugins.MyMetrixLiteOther.runningTextStartdelay.value)
				speed = str(config.plugins.MyMetrixLiteOther.runningTextSpeed.value)
				EMCSkinSearchAndReplace.append(['movetype=none,startdelay=600,steptime=60', f'movetype=running,startdelay={delay},steptime={speed}'])

			skin_lines = appendSkinFile(SKIN_EMC_SOURCE, EMCSkinSearchAndReplace)

			xFile = open(SKIN_EMC_TARGET_TMP, "w")
			for xx in skin_lines:
				xFile.writelines(xx)
			xFile.close()

			################
			# Design
			################

			DESIGNSkinSearchAndReplace = []

			#SkinDesign
			confvalue = config.plugins.MyMetrixLiteOther.SkinDesignLUC.getValue()
			if confvalue != "no":
				color = (config.plugins.MyMetrixLiteColors.upperleftcornertransparency.value + config.plugins.MyMetrixLiteColors.upperleftcornerbackground.value)
				width = config.plugins.MyMetrixLiteOther.SkinDesignLUCwidth.value
				height = config.plugins.MyMetrixLiteOther.SkinDesignLUCheight.value
				posx = 0
				posy = 0
				posz = -105 + int(config.plugins.MyMetrixLiteOther.SkinDesignLUCposz.value)
				newlines = f"<eLabel name=\"upperleftcorner-s\" position=\"{posx},{posy}\" zPosition=\"{posz}\" size=\"{width},{height}\" backgroundColor=\"#{color}\" />"
				newlinem = f"<eLabel name=\"upperleftcorner-m\" position=\"{posx},{posy}\" zPosition=\"{posz}\" size=\"{width},{height}\" backgroundColor=\"#{color}\" />"
				if confvalue == "both":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="upperleftcorner-s" position="0,0" zPosition="-105" size="40,25" backgroundColor="#1A27408B" /-->', newlines])
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="upperleftcorner-m" position="0,0" zPosition="-105" size="40,25" backgroundColor="#1A27408B" /-->', newlinem])
				elif confvalue == "screens":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="upperleftcorner-s" position="0,0" zPosition="-105" size="40,25" backgroundColor="#1A27408B" /-->', newlines])
				elif confvalue == "menus":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="upperleftcorner-m" position="0,0" zPosition="-105" size="40,25" backgroundColor="#1A27408B" /-->', newlinem])

			confvalue = config.plugins.MyMetrixLiteOther.SkinDesignLLC.getValue()
			if confvalue != "no":
				color = (config.plugins.MyMetrixLiteColors.lowerleftcornertransparency.value + config.plugins.MyMetrixLiteColors.lowerleftcornerbackground.value)
				width = config.plugins.MyMetrixLiteOther.SkinDesignLLCwidth.value
				height = int(config.plugins.MyMetrixLiteOther.SkinDesignLLCheight.value)
				posx = 0
				posy = 720 - height
				posz = -105 + int(config.plugins.MyMetrixLiteOther.SkinDesignLLCposz.value)
				newlines = f"<eLabel name=\"lowerleftcorner-s\" position=\"{posx},{posy}\" zPosition=\"{posz}\" size=\"{width},{height}\" backgroundColor=\"#{color}\" />"
				newlinem = f"<eLabel name=\"lowerleftcorner-m\" position=\"{posx},{posy}\" zPosition=\"{posz}\" size=\"{width},{height}\" backgroundColor=\"#{color}\" />"
				if confvalue == "both":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="lowerleftcorner-s" position="0,675" zPosition="-105" size="40,45" backgroundColor="#1A27408B" /-->', newlines])
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="lowerleftcorner-m" position="0,675" zPosition="-105" size="40,45" backgroundColor="#1A27408B" /-->', newlinem])
				elif confvalue == "screens":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="lowerleftcorner-s" position="0,675" zPosition="-105" size="40,45" backgroundColor="#1A27408B" /-->', newlines])
				elif confvalue == "menus":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="lowerleftcorner-m" position="0,675" zPosition="-105" size="40,45" backgroundColor="#1A27408B" /-->', newlinem])

			confvalue = config.plugins.MyMetrixLiteOther.SkinDesignRUC.getValue()
			if confvalue != "no":
				color = (config.plugins.MyMetrixLiteColors.upperrightcornertransparency.value + config.plugins.MyMetrixLiteColors.upperrightcornerbackground.value)
				width = int(config.plugins.MyMetrixLiteOther.SkinDesignRUCwidth.value)
				height = config.plugins.MyMetrixLiteOther.SkinDesignRUCheight.value
				posx = 1280 - width
				posy = 0
				posz = -105 + int(config.plugins.MyMetrixLiteOther.SkinDesignRUCposz.value)
				newlines = f"<eLabel name=\"upperrightcorner-s\" position=\"{posx},{posy}\" zPosition=\"{posz}\" size=\"{width},{height}\" backgroundColor=\"#{color}\" />"
				newlinem = f"<eLabel name=\"upperrightcorner-m\" position=\"{posx},{posy}\" zPosition=\"{posz}\" size=\"{width},{height}\" backgroundColor=\"#{color}\" />"
				if confvalue == "both":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="upperrightcorner-s" position="1240,0" zPosition="-105" size="40,60" backgroundColor="#1A0F0F0F" /-->', newlines])
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="upperrightcorner-m" position="1240,0" zPosition="-105" size="40,60" backgroundColor="#1A0F0F0F" /-->', newlinem])
				elif confvalue == "screens":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="upperrightcorner-s" position="1240,0" zPosition="-105" size="40,60" backgroundColor="#1A0F0F0F" /-->', newlines])
				elif confvalue == "menus":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="upperrightcorner-m" position="1240,0" zPosition="-105" size="40,60" backgroundColor="#1A0F0F0F" /-->', newlinem])

			confvalue = config.plugins.MyMetrixLiteOther.SkinDesignRLC.getValue()
			if confvalue != "no":
				color = (config.plugins.MyMetrixLiteColors.lowerrightcornertransparency.value + config.plugins.MyMetrixLiteColors.lowerrightcornerbackground.value)
				width = int(config.plugins.MyMetrixLiteOther.SkinDesignRLCwidth.value)
				height = int(config.plugins.MyMetrixLiteOther.SkinDesignRLCheight.value)
				posx = 1280 - width
				posy = 720 - height
				posz = -105 + int(config.plugins.MyMetrixLiteOther.SkinDesignRLCposz.value)
				newlines = f"<eLabel name=\"lowerrightcorner-s\" position=\"{posx},{posy}\" zPosition=\"{posz}\" size=\"{width},{height}\" backgroundColor=\"#{color}\" />"
				newlinem = f"<eLabel name=\"lowerrightcorner-m\" position=\"{posx},{posy}\" zPosition=\"{posz}\" size=\"{width},{height}\" backgroundColor=\"#{color}\" />"
				if confvalue == "both":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="lowerrightcorner-s" position="1240,640" zPosition="-105" size="40,80" backgroundColor="#1A0F0F0F" /-->', newlines])
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="lowerrightcorner-m" position="1240,640" zPosition="-105" size="40,80" backgroundColor="#1A0F0F0F" /-->', newlinem])
				elif confvalue == "screens":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="lowerrightcorner-s" position="1240,640" zPosition="-105" size="40,80" backgroundColor="#1A0F0F0F" /-->', newlines])
				elif confvalue == "menus":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="lowerrightcorner-m" position="1240,640" zPosition="-105" size="40,80" backgroundColor="#1A0F0F0F" /-->', newlinem])

			confvalue = config.plugins.MyMetrixLiteOther.SkinDesignOLH.getValue()
			if confvalue != "no":
				color = (config.plugins.MyMetrixLiteColors.optionallayerhorizontaltransparency.value + config.plugins.MyMetrixLiteColors.optionallayerhorizontalbackground.value)
				width = config.plugins.MyMetrixLiteOther.SkinDesignOLHwidth.value
				height = config.plugins.MyMetrixLiteOther.SkinDesignOLHheight.value
				posx = config.plugins.MyMetrixLiteOther.SkinDesignOLHposx.value
				posy = config.plugins.MyMetrixLiteOther.SkinDesignOLHposy.value
				posz = -105 + int(config.plugins.MyMetrixLiteOther.SkinDesignOLHposz.value)
				newlines = f"<eLabel name=\"optionallayerhorizontal-s\" position=\"{posx},{posy}\" zPosition=\"{posz}\" size=\"{width},{height}\" backgroundColor=\"#{color}\" />"
				newlinem = f"<eLabel name=\"optionallayerhorizontal-m\" position=\"{posx},{posy}\" zPosition=\"{posz}\" size=\"{width},{height}\" backgroundColor=\"#{color}\" />"
				if confvalue == "both":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="optionallayerhorizontal-s" position="0,655" zPosition="-105" size="1127,30" backgroundColor="#1A27408B" /-->', newlines])
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="optionallayerhorizontal-m" position="0,655" zPosition="-105" size="1127,30" backgroundColor="#1A27408B" /-->', newlinem])
				elif confvalue == "screens":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="optionallayerhorizontal-s" position="0,655" zPosition="-105" size="1127,30" backgroundColor="#1A27408B" /-->', newlines])
				elif confvalue == "menus":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="optionallayerhorizontal-m" position="0,655" zPosition="-105" size="1127,30" backgroundColor="#1A27408B" /-->', newlinem])

			confvalue = config.plugins.MyMetrixLiteOther.SkinDesignOLV.getValue()
			if confvalue != "no":
				color = (config.plugins.MyMetrixLiteColors.optionallayerverticaltransparency.value + config.plugins.MyMetrixLiteColors.optionallayerverticalbackground.value)
				width = config.plugins.MyMetrixLiteOther.SkinDesignOLVwidth.value
				height = config.plugins.MyMetrixLiteOther.SkinDesignOLVheight.value
				posx = config.plugins.MyMetrixLiteOther.SkinDesignOLVposx.value
				posy = config.plugins.MyMetrixLiteOther.SkinDesignOLVposy.value
				posz = -105 + int(config.plugins.MyMetrixLiteOther.SkinDesignOLVposz.value)
				newlines = f"<eLabel name=\"optionallayervertical-s\" position=\"{posx},{posy}\" zPosition=\"{posz}\" size=\"{width},{height}\" backgroundColor=\"#{color}\" />"
				newlinem = f"<eLabel name=\"optionallayervertical-m\" position=\"{posx},{posy}\" zPosition=\"{posz}\" size=\"{width},{height}\" backgroundColor=\"#{color}\" />"
				if confvalue == "both":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="optionallayervertical-s" position="102,51" zPosition="-105" size="60,669" backgroundColor="#1A27408B" /-->', newlines])
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="optionallayervertical-m" position="102,51" zPosition="-105" size="60,669" backgroundColor="#1A27408B" /-->', newlinem])
				elif confvalue == "screens":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="optionallayervertical-s" position="102,51" zPosition="-105" size="60,669" backgroundColor="#1A27408B" /-->', newlines])
				elif confvalue == "menus":
					DESIGNSkinSearchAndReplace.append(['<!--eLabel name="optionallayervertical-m" position="102,51" zPosition="-105" size="60,669" backgroundColor="#1A27408B" /-->', newlinem])

			if config.plugins.MyMetrixLiteOther.layeraunderlineshowmainlayer.value:
				DESIGNSkinSearchAndReplace.append(['<!--eLabel name="underline" position="40,88" size="1200,1" backgroundColor="layer-a-underline" zPosition="-1" /-->', '<eLabel name="underline" position="40,88" size="1200,1" backgroundColor="layer-a-underline" zPosition="-1" />'])
				DESIGNSkinSearchAndReplace.append(['<!--eLabel name="underline" position="40,88" size="755,1" backgroundColor="layer-a-underline" zPosition="-1" /-->', '<eLabel name="underline" position="40,88" size="755,1" backgroundColor="layer-a-underline" zPosition="-1" />'])

			if config.plugins.MyMetrixLiteOther.SkinDesignSpace.getValue() is True:
				newline1 = ('<panel name="template1_2layer-' + config.plugins.MyMetrixLiteOther.SkinDesign.value + 's" />')
				newline2 = ('<panel name="INFOBAREPGWIDGET_Layer-' + config.plugins.MyMetrixLiteOther.SkinDesign.value + 's" />')
				newline3 = ('<panel name="QuickMenu_Layer-' + config.plugins.MyMetrixLiteOther.SkinDesign.value + 's" />')
				DESIGNSkinSearchAndReplace.append(['eLabel name="underline" position="40,88" size="755,1"', 'eLabel name="underline" position="40,88" size="750,1"'])
			else:
				newline1 = ('<panel name="template1_2layer-' + config.plugins.MyMetrixLiteOther.SkinDesign.value + '" />')
				newline2 = ('<panel name="INFOBAREPGWIDGET_Layer-' + config.plugins.MyMetrixLiteOther.SkinDesign.value + '" />')
				newline3 = ('<panel name="QuickMenu_Layer-' + config.plugins.MyMetrixLiteOther.SkinDesign.value + '" />')
			DESIGNSkinSearchAndReplace.append(['<panel name="template1_2layer-1" />', newline1])
			DESIGNSkinSearchAndReplace.append(['<panel name="INFOBAREPGWIDGET_Layer-1" />', newline2])
			DESIGNSkinSearchAndReplace.append(['<panel name="QuickMenu_Layer-1" />', newline3])

			if int(config.plugins.MyMetrixLiteOther.SkinDesign.value) > 1:
				DESIGNSkinSearchAndReplace.append(['<ePixmap position="950,600" size="81,40" zPosition="10" pixmap="buttons/', '<ePixmap position="950,635" size="81,40" zPosition="10" pixmap="buttons/'])
				DESIGNSkinSearchAndReplace.append(['<ePixmap position="1045,600" size="81,40" zPosition="10" pixmap="buttons/', '<ePixmap position="1045,635" size="81,40" zPosition="10" pixmap="buttons/'])
				DESIGNSkinSearchAndReplace.append(['<ePixmap position="1140,600" size="81,40" zPosition="10" pixmap="buttons/', '<ePixmap position="1140,635" size="81,40" zPosition="10" pixmap="buttons/'])

			DESIGNSkinSearchAndReplace.append(['<panel name="INFOBAREXTENDEDINFO-1" />', '<panel name="INFOBAREXTENDEDINFO-' + config.plugins.MyMetrixLiteOther.ExtendedinfoStyle.value + '" />'])

			# color gradient for ib,sib,mb,ibepg and quickemenu
			if config.plugins.MyMetrixLiteColors.cologradient.value != '0':
				old = '<!--ePixmap alphatest="blend" pixmap="colorgradient_bottom_ib.png" position="0,560" size="1280,160" zPosition="-1" /-->'
				new = '<ePixmap alphatest="blend" pixmap="colorgradient_bottom_ib.png" position="0,560" size="1280,160" zPosition="-1" />'
				DESIGNSkinSearchAndReplace.append([old, new])
				old = '<!--ePixmap alphatest="blend" pixmap="colorgradient_bottom_epg.png" position="0,10" size="1280,220" zPosition="-1" /-->'
				new = '<ePixmap alphatest="blend" pixmap="colorgradient_bottom_epg.png" position="0,10" size="1280,220" zPosition="-1" />'
				DESIGNSkinSearchAndReplace.append([old, new])
				old = '<!--ePixmap alphatest="blend" pixmap="colorgradient_top_ib.png" position="0,0" size="1280,30" zPosition="-1" /-->'
				new = '<ePixmap alphatest="blend" pixmap="colorgradient_top_ib.png" position="0,0" size="1280,30" zPosition="-1" />'
				DESIGNSkinSearchAndReplace.append([old, new])
				old = '<!--ePixmap alphatest="blend" pixmap="colorgradient_top_qm.png" position="0,0" size="1280,94" zPosition="-1" /-->'
				new = '<ePixmap alphatest="blend" pixmap="colorgradient_top_qm.png" position="0,0" size="1280,94" zPosition="-1" />'
				DESIGNSkinSearchAndReplace.append([old, new])
				old = '<!--ePixmap alphatest="blend" pixmap="colorgradient_bottom_mb.png" position="0,570" size="1280,150" zPosition="-1" /-->'
				new = '<ePixmap alphatest="blend" pixmap="colorgradient_bottom_mb.png" position="0,570" size="1280,150" zPosition="-1" />'
				DESIGNSkinSearchAndReplace.append([old, new])
				old = '<!--ePixmap alphatest="blend" pixmap="colorgradient_bottom_pb.png" position="0,640" size="1280,80" zPosition="-1" /-->'
				new = '<ePixmap alphatest="blend" pixmap="colorgradient_bottom_pb.png" position="0,640" size="1280,80" zPosition="-1" />'
				DESIGNSkinSearchAndReplace.append([old, new])

			#picon
			if config.plugins.MyMetrixLiteOther.SkinDesignInfobarPicon.value == "1":
				posx = 33 + config.plugins.MyMetrixLiteOther.SkinDesignInfobarXPiconPosX.value
				posy = 574 + config.plugins.MyMetrixLiteOther.SkinDesignInfobarXPiconPosY.value
				old = '<widget alphatest="blend" position="33,574" size="220,132" render="MetrixHDXPicon" source="session.CurrentService" transparent="1" zPosition="4">'
				new = '<widget alphatest="blend" position="' + str(posx) + ',' + str(posy) + '" size="220,132" render="MetrixHDXPicon" source="session.CurrentService" transparent="1" zPosition="4">'
			else:
				sizex = 267 + int(config.plugins.MyMetrixLiteOther.SkinDesignInfobarZZZPiconSize.value * 1.66)
				sizey = 160 + int(config.plugins.MyMetrixLiteOther.SkinDesignInfobarZZZPiconSize.value)
				posx = 0 + config.plugins.MyMetrixLiteOther.SkinDesignInfobarZZZPiconPosX.value
				posy = 560 + config.plugins.MyMetrixLiteOther.SkinDesignInfobarZZZPiconPosY.value
				old = '<widget alphatest="blend" position="0,560" size="267,160" render="MetrixHDXPicon" source="session.CurrentService" transparent="1" zPosition="4">'
				new = '<widget alphatest="blend" position="' + str(posx) + ',' + str(posy) + '" size="' + str(sizex) + ',' + str(sizey) + '" render="MetrixHDXPicon" source="session.CurrentService" transparent="1" zPosition="4">'
				DESIGNSkinSearchAndReplace.append(['<panel name="IB_XPicon" />', '<panel name="IB_ZZZPicon" />'])
			DESIGNSkinSearchAndReplace.append([old, new])

			#pvr state
			if config.plugins.MyMetrixLiteOther.showPVRState.getValue() > "1":
				DESIGNSkinSearchAndReplace.append(['<screen name="PVRState" position="230,238"', '<screen name="PVRState_Standard" position="230,238"'])
				DESIGNSkinSearchAndReplace.append(['<screen name="PVRState_Top" position="0,0"', '<screen name="PVRState" position="0,0"'])
				if config.plugins.MyMetrixLiteOther.showPVRState.getValue() == "3":
					DESIGNSkinSearchAndReplace.append(['<!--panel name="PVRState_3_ct" /-->', '<panel name="PVRState_3_ct" />'])
				if config.plugins.MyMetrixLiteOther.showMovieTime.getValue() == "3":
					DESIGNSkinSearchAndReplace.append(['<!--panel name="PVRState_3_mt" /-->', '<panel name="PVRState_3_mt" />'])
			else:
				if config.plugins.MyMetrixLiteOther.showMovieTime.getValue() == "3":
					DESIGNSkinSearchAndReplace.append(['<panel name="PVRState_1" />', '<panel name="PVRState_2" />'])

			#graphical epg style
			if config.plugins.MyMetrixLiteOther.graphicalEpgStyle.getValue() == "2":
				DESIGNSkinSearchAndReplace.append(['<panel name="GraphicalEPG_1" />', '<panel name="GraphicalEPG_2" />'])
				DESIGNSkinSearchAndReplace.append(['<panel name="GraphicalEPGPIG_1" />', '<panel name="GraphicalEPGPIG_2" />'])

			if config.plugins.MyMetrixLiteOther.showChannelListScrollbar.value:
				mode = "showOnDemand"
			else:
				mode = "showNever"
			margin = str(config.plugins.MyMetrixLiteOther.setFieldMargin.value)
			distance = str(config.plugins.MyMetrixLiteOther.setItemDistance.value)
			DESIGNSkinSearchAndReplace.append(['scrollbarMode="showNever" fieldMargins="5" itemsDistances="5"', f'scrollbarMode="{mode}" fieldMargins="{margin}" itemsDistances="{distance}"'])

			delay = config.plugins.MyMetrixLiteOther.runningTextStartdelay.value
			speed = config.plugins.MyMetrixLiteOther.runningTextSpeed.value
			if config.plugins.MyMetrixLiteOther.showChannelListRunningtext.value:
				DESIGNSkinSearchAndReplace.append(['movetype=none,startdelay=600,steptime=60', f'movetype=running,startdelay={delay},steptime={speed}'])  # event description
			if config.plugins.MyMetrixLiteOther.showInfoBarRunningtext.value:
				DESIGNSkinSearchAndReplace.append(['movetype=none,startdelay=900,steptime=1,step=3', f'movetype=running,startdelay={int(delay * 1.5)},steptime={speed},step=2'])  # infobar

			#show menu buttons
			if not config.plugins.MyMetrixLiteOther.SkinDesignMenuButtons.value:
				DESIGNSkinSearchAndReplace.append(['<panel name="MenuButtons_template"/>', '<!--panel name="MenuButtons_template"/-->'])

			skin_lines = appendSkinFile(SKIN_DESIGN_SOURCE, DESIGNSkinSearchAndReplace)

			xFile = open(SKIN_DESIGN_TARGET_TMP, "w")
			for xx in skin_lines:
				if '<eLabel name="underline"' in xx:
					xx = sub(r'(name="underline" +position=" *)(\d+)( *, *)(\d+)(" +size=" *)(\d+)( *, *)(\d+)', self.linereplacer, xx)
				xFile.writelines(xx)
			xFile.close()

			################
			# Skin
			################

			skinSearchAndReplace = []
			orgskinSearchAndReplace = []  # needed for some attributes (e.g. borderset setting was lost after using plugin media portal - because restored settings from skin.xml and not from skin.MySkin.xml)
			skinSearchAndReplace.append(['<!-- original file -->', ''])
			orgskinSearchAndReplace.append(['<!-- original file -->', '<!-- !!!copied and changed file!!! -->'])

			#Borderset screens
			w = 5
			wt = 50
			if self.EHDenabled:
				w *= self.EHDfactor
				wt *= self.EHDfactor
			width = f"{w}px"
			width_top = f"{wt}px"

			color = config.plugins.MyMetrixLiteColors.windowborder_top.value
			if exists(f"/usr/share/enigma2/MetrixHD/border/{width_top}/{color}.png"):
				newline = f"<pixmap pos=\"bpTop\" filename=\"MetrixHD/border/{width_top}/{color}.png\" />"
				skinSearchAndReplace.append(['<pixmap pos="bpTop" filename="MetrixHD/border/50px/0F0F0F.png" />', newline])
				orgskinSearchAndReplace.append(['<pixmap pos="bpTop" filename="MetrixHD/border/50px/0F0F0F.png" />', newline])
			color = config.plugins.MyMetrixLiteColors.windowborder_bottom.value
			if exists(f"/usr/share/enigma2/MetrixHD/border/{width}/{color}.png"):
				newline = f"<pixmap pos=\"bpBottom\" filename=\"MetrixHD/border/{width}/{color}.png\" />"
				skinSearchAndReplace.append(['<pixmap pos="bpBottom" filename="MetrixHD/border/5px/0F0F0F.png" />', newline])
				orgskinSearchAndReplace.append(['<pixmap pos="bpBottom" filename="MetrixHD/border/5px/0F0F0F.png" />', newline])
			color = config.plugins.MyMetrixLiteColors.windowborder_left.value
			if exists(f"/usr/share/enigma2/MetrixHD/border/{width}/{color}.png"):
				newline = f"<pixmap pos=\"bpLeft\" filename=\"MetrixHD/border/{width}/{color}.png\" />"
				skinSearchAndReplace.append(['<pixmap pos="bpLeft" filename="MetrixHD/border/5px/0F0F0F.png" />', newline])
				orgskinSearchAndReplace.append(['<pixmap pos="bpLeft" filename="MetrixHD/border/5px/0F0F0F.png" />', newline])
			color = config.plugins.MyMetrixLiteColors.windowborder_right.value
			if exists(f"/usr/share/enigma2/MetrixHD/border/{width}/{color}.png"):
				newline = f"<pixmap pos=\"bpRight\" filename=\"MetrixHD/border/{width}/{color}.png\" />"
				skinSearchAndReplace.append(['<pixmap pos="bpRight" filename="MetrixHD/border/5px/0F0F0F.png" />', newline])
				orgskinSearchAndReplace.append(['<pixmap pos="bpRight" filename="MetrixHD/border/5px/0F0F0F.png" />', newline])

			#Border listbox
			width = config.plugins.MyMetrixLiteColors.listboxborder_topwidth.value
			if width != "no":
				color = config.plugins.MyMetrixLiteColors.listboxborder_top.value
				if exists(f"/usr/share/enigma2/MetrixHD/border/{width}/{color}.png"):
					newline = f"<pixmap pos=\"bpTop\" filename=\"MetrixHD/border/{width}/{color}.png\" />"
					skinSearchAndReplace.append(['<!--lb pixmap pos="bpTop" filename="MetrixHD/border/1px/FFFFFF.png" /-->', newline])
					orgskinSearchAndReplace.append(['<!--lb pixmap pos="bpTop" filename="MetrixHD/border/1px/FFFFFF.png" /-->', newline])
			width = config.plugins.MyMetrixLiteColors.listboxborder_bottomwidth.value
			if width != "no":
				color = config.plugins.MyMetrixLiteColors.listboxborder_bottom.value
				if exists(f"/usr/share/enigma2/MetrixHD/border/{width}/{color}.png"):
					newline = f"<pixmap pos=\"bpBottom\" filename=\"MetrixHD/border/{width}/{color}.png\" />"
					skinSearchAndReplace.append(['<!--lb pixmap pos="bpBottom" filename="MetrixHD/border/1px/FFFFFF.png" /-->', newline])
					orgskinSearchAndReplace.append(['<!--lb pixmap pos="bpBottom" filename="MetrixHD/border/1px/FFFFFF.png" /-->', newline])
			width = config.plugins.MyMetrixLiteColors.listboxborder_leftwidth.value
			if width != "no":
				color = config.plugins.MyMetrixLiteColors.listboxborder_left.value
				if exists(f"/usr/share/enigma2/MetrixHD/border/{width}/{color}.png"):
					newline = f"<pixmap pos=\"bpLeft\" filename=\"MetrixHD/border/{width}/{color}.png\" />"
					skinSearchAndReplace.append(['<!--lb pixmap pos="bpLeft" filename="MetrixHD/border/1px/FFFFFF.png" /-->', newline])
					orgskinSearchAndReplace.append(['<!--lb pixmap pos="bpLeft" filename="MetrixHD/border/1px/FFFFFF.png" /-->', newline])
			width = config.plugins.MyMetrixLiteColors.listboxborder_rightwidth.value
			if width != "no":
				color = config.plugins.MyMetrixLiteColors.listboxborder_right.value
				if exists(f"/usr/share/enigma2/MetrixHD/border/{width}/{color}.png"):
					newline = f"<pixmap pos=\"bpRight\" filename=\"MetrixHD/border/{width}/{color}.png\" />"
					skinSearchAndReplace.append(['<!--lb pixmap pos="bpRight" filename="MetrixHD/border/1px/FFFFFF.png" /-->', newline])
					orgskinSearchAndReplace.append(['<!--lb pixmap pos="bpRight" filename="MetrixHD/border/1px/FFFFFF.png" /-->', newline])

			#fonts system
			type = config.plugins.MyMetrixLiteFonts.Lcd_type.value
			scale = config.plugins.MyMetrixLiteFonts.Lcd_scale.value
			old = '<font filename="/usr/share/fonts/lcd.ttf" name="LCD" scale="100" />'
			new = '<font filename="' + type + '" name="LCD" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.Replacement_type.value
			scale = config.plugins.MyMetrixLiteFonts.Replacement_scale.value
			old = '<font filename="/usr/share/fonts/ae_AlMateen.ttf" name="Replacement" scale="100" replacement="1" />'
			new = '<font filename="' + type + '" name="Replacement" scale="' + str(scale) + '" replacement="1" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.Console_type.value
			scale = config.plugins.MyMetrixLiteFonts.Console_scale.value
			old = '<font filename="/usr/share/fonts/tuxtxt.ttf" name="Console" scale="100" />'
			new = '<font filename="' + type + '" name="Console" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.Fixed_type.value
			scale = config.plugins.MyMetrixLiteFonts.Fixed_scale.value
			old = '<font filename="/usr/share/fonts/andale.ttf" name="Fixed" scale="100" />'
			new = '<font filename="' + type + '" name="Fixed" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.Arial_type.value
			scale = config.plugins.MyMetrixLiteFonts.Arial_scale.value
			old = '<font filename="/usr/share/fonts/nmsbd.ttf" name="Arial" scale="100" />'
			new = '<font filename="' + type + '" name="Arial" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			#fonts skin
			type = config.plugins.MyMetrixLiteFonts.Regular_type.value
			scale = config.plugins.MyMetrixLiteFonts.Regular_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/OpenSans-Regular.ttf" name="Regular" scale="95" />'
			new = '<font filename="' + type + '" name="Regular" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.RegularLight_type.value
			scale = config.plugins.MyMetrixLiteFonts.RegularLight_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/OpenSans-Regular.ttf" name="RegularLight" scale="95" />'
			new = '<font filename="' + type + '" name="RegularLight" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.SetrixHD_type.value
			scale = config.plugins.MyMetrixLiteFonts.SetrixHD_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="SetrixHD" scale="100" />'
			new = '<font filename="' + type + '" name="SetrixHD" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

#			scale = config.plugins.MyMetrixLiteFonts.Meteo_scale.value
#			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/meteocons.ttf" name="Meteo" scale="100" />'
#			new = '<font filename="/usr/share/enigma2/MetrixHD/fonts/meteocons.ttf" name="Meteo" scale="' + str(scale) + '" />'
#			if exists(type):
#				skinSearchAndReplace.append([old, new])

			#global
			type = config.plugins.MyMetrixLiteFonts.globaltitle_type.value
			scale = config.plugins.MyMetrixLiteFonts.globaltitle_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="global_title" scale="100" />'
			new = '<font filename="' + type + '" name="global_title" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.globalbutton_type.value
			scale = config.plugins.MyMetrixLiteFonts.globalbutton_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="global_button" scale="90" />'
			new = '<font filename="' + type + '" name="global_button" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.globalclock_type.value
			scale = config.plugins.MyMetrixLiteFonts.globalclock_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="global_clock" scale="100" />'
			new = '<font filename="' + type + '" name="global_clock" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.globalweatherweek_type.value
			scale = config.plugins.MyMetrixLiteFonts.globalweatherweek_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/DroidSans-Bold.ttf" name="global_weather_bold" scale="100" />'
			new = '<font filename="' + type + '" name="global_weather_bold" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.globallarge_type.value
			scale = config.plugins.MyMetrixLiteFonts.globallarge_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="global_large" scale="100" />'
			new = '<font filename="' + type + '" name="global_large" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])
			else:
				type = "/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf"

			if config.plugins.MyMetrixLiteOther.SkinDesignShowLargeText.value == "both":
				old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="global_large_menu" scale="100" />'
				new = '<font filename="' + type + '" name="global_large_menu" scale="' + str(scale) + '" />'
				skinSearchAndReplace.append([old, new])
				old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="global_large_screen" scale="100" />'
				new = '<font filename="' + type + '" name="global_large_screen" scale="' + str(scale) + '" />'
				skinSearchAndReplace.append([old, new])
			elif config.plugins.MyMetrixLiteOther.SkinDesignShowLargeText.value == "menus":
				old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="global_large_menu" scale="100" />'
				new = '<font filename="' + type + '" name="global_large_menu" scale="' + str(scale) + '" />'
				skinSearchAndReplace.append([old, new])
				old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="global_large_screen" scale="100" />'
				new = '<font filename="' + type + '" name="global_large_screen" scale="0" />'
				skinSearchAndReplace.append([old, new])
			elif config.plugins.MyMetrixLiteOther.SkinDesignShowLargeText.value == "screens":
				old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="global_large_menu" scale="100" />'
				new = '<font filename="' + type + '" name="global_large_menu" scale="0" />'
				skinSearchAndReplace.append([old, new])
				old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="global_large_screen" scale="100" />'
				new = '<font filename="' + type + '" name="global_large_screen" scale="' + str(scale) + '" />'
				skinSearchAndReplace.append([old, new])
			else:
				old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="global_large_menu" scale="100" />'
				new = '<font filename="' + type + '" name="global_large_menu" scale="0" />'
				skinSearchAndReplace.append([old, new])
				old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="global_large_screen" scale="100" />'
				new = '<font filename="' + type + '" name="global_large_screen" scale="0" />'
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.globalsmall_type.value
			scale = config.plugins.MyMetrixLiteFonts.globalsmall_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/OpenSans-Regular.ttf" name="global_small" scale="95" />'
			new = '<font filename="' + type + '" name="global_small" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.globalmenu_type.value
			scale = config.plugins.MyMetrixLiteFonts.globalmenu_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="global_menu" scale="100" />'
			new = '<font filename="' + type + '" name="global_menu" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			#screens
			type = config.plugins.MyMetrixLiteFonts.screenlabel_type.value
			scale = config.plugins.MyMetrixLiteFonts.screenlabel_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/OpenSans-Regular.ttf" name="screen_label" scale="95" />'
			new = '<font filename="' + type + '" name="screen_label" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.screentext_type.value
			scale = config.plugins.MyMetrixLiteFonts.screentext_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/OpenSans-Regular.ttf" name="screen_text" scale="95" />'
			new = '<font filename="' + type + '" name="screen_text" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.screeninfo_type.value
			scale = config.plugins.MyMetrixLiteFonts.screeninfo_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="screen_info" scale="100" />'
			new = '<font filename="' + type + '" name="screen_info" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			#channellist
			type = config.plugins.MyMetrixLiteFonts.epgevent_type.value
			scale = config.plugins.MyMetrixLiteFonts.epgevent_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/OpenSans-Regular.ttf" name="epg_event" scale="95" />'
			new = '<font filename="' + type + '" name="epg_event" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.epgtext_type.value
			scale = config.plugins.MyMetrixLiteFonts.epgtext_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/OpenSans-Regular.ttf" name="epg_text" scale="95" />'
			new = '<font filename="' + type + '" name="epg_text" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.epginfo_type.value
			scale = config.plugins.MyMetrixLiteFonts.epginfo_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/OpenSans-Regular.ttf" name="epg_info" scale="95" />'
			new = '<font filename="' + type + '" name="epg_info" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			#infobar
			type = config.plugins.MyMetrixLiteFonts.infobarevent_type.value
			scale = config.plugins.MyMetrixLiteFonts.infobarevent_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf" name="infobar_event" scale="100" />'
			new = '<font filename="' + type + '" name="infobar_event" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			type = config.plugins.MyMetrixLiteFonts.infobartext_type.value
			scale = config.plugins.MyMetrixLiteFonts.infobartext_scale.value
			old = '<font filename="/usr/share/enigma2/MetrixHD/fonts/OpenSans-Regular.ttf" name="infobar_text" scale="95" />'
			new = '<font filename="' + type + '" name="infobar_text" scale="' + str(scale) + '" />'
			if exists(type):
				skinSearchAndReplace.append([old, new])

			#skinfiles
			skinSearchAndReplace.append([SKIN_INFOBAR_SOURCE, SKIN_INFOBAR_TARGET])
			skinSearchAndReplace.append([SKIN_INFOBAR_LITE_SOURCE, SKIN_INFOBAR_LITE_TARGET])
			skinSearchAndReplace.append([SKIN_SECOND_INFOBAR_SOURCE, SKIN_SECOND_INFOBAR_TARGET])
			skinSearchAndReplace.append([SKIN_SECOND_INFOBAR_ECM_SOURCE, SKIN_SECOND_INFOBAR_ECM_TARGET])
			skinSearchAndReplace.append([SKIN_CHANNEL_SELECTION_SOURCE, SKIN_CHANNEL_SELECTION_TARGET])
			skinSearchAndReplace.append([SKIN_OPENATV_SOURCE, SKIN_OPENATV_TARGET])
			skinSearchAndReplace.append([SKIN_PLUGINS_SOURCE, SKIN_PLUGINS_TARGET])
			skinSearchAndReplace.append([SKIN_MOVIEPLAYER_SOURCE, SKIN_MOVIEPLAYER_TARGET])
			skinSearchAndReplace.append([SKIN_EMC_SOURCE, SKIN_EMC_TARGET])
			skinSearchAndReplace.append([SKIN_UNCHECKED_SOURCE, SKIN_UNCHECKED_TARGET])
			skinSearchAndReplace.append([SKIN_TEMPLATES_SOURCE, SKIN_TEMPLATES_TARGET])
			skinSearchAndReplace.append([SKIN_DESIGN_SOURCE, SKIN_DESIGN_TARGET])

			#make skin file
			skin_lines = appendSkinFile(SKIN_SOURCE, skinSearchAndReplace)
			orgskin_lines = appendSkinFile(SKIN_SOURCE + bname, orgskinSearchAndReplace)

			xFile = open(SKIN_TARGET_TMP, "w")
			for xx in skin_lines:
				xFile.writelines(xx)
			xFile.close()

			# write changed skin.xml
			xFile = open(SKIN_SOURCE, "w")
			for xx in orgskin_lines:
				xFile.writelines(xx)
			xFile.close()

			################
			# Icons, Graphics
			################

			# update *.png files
			self.updateIcons(self.EHDres)
			self.makeGraphics(self.EHDfactor)

			################
			# Skinparts
			################

			mySkindir = '/usr/share/enigma2/MetrixHD/mySkin/'
			skinpartdir = '/usr/share/enigma2/MetrixHD/skinparts/'
			# skinparts = ''
			if not exists(mySkindir):
				mkdir(mySkindir)
			else:
				for file in listdir(mySkindir):
					if isfile(mySkindir + file):
						remove(mySkindir + file)
			for skinpart in listdir(skinpartdir):
				if isfile(skinpartdir + skinpart):
					continue
				enabled = False
				partname = partpath = ''
				for file in listdir(skinpartdir + skinpart):
					filepath = pathjoin(skinpartdir + skinpart, file)
					if not isfile(filepath):
						continue
					if file == skinpart + '.xml':
						partname = skinpart
						partpath = filepath
						TARGETpath = mySkindir + 'skin_' + skinpart + '.mySkin.xml'
						TMPpath = skinpartdir + skinpart + '/' + skinpart + '.mySkin.xml.tmp'
						#remove old MySkin files
						if isfile(TMPpath.replace('.tmp', '')):
							remove(TMPpath.replace('.tmp', ''))
					if file == 'enabled':
						enabled = True
				if partname and enabled:
					skinfiles.append((partpath, TARGETpath, TMPpath))

			################
			# EHD-skin
			################

			#EHD-variables
			self.skinline_error = False
			self.pixmap_error = False
			self.round_par = int(config.plugins.MyMetrixLiteOther.EHDrounddown.value)
			self.font_offset = config.plugins.MyMetrixLiteOther.EHDfontoffset.value
			if config.plugins.MyMetrixLiteOther.SkinDesignInfobarPicon.value == "1":
				self.picon_zoom = 1 + ((self.EHDfactor - 1) * float(config.plugins.MyMetrixLiteOther.EHDpiconzoom.value))
				if not self.picon_zoom:
					self.picon_zoom = 1
			else:
				self.picon_zoom = self.EHDfactor

			#make *_TARGET files
			print(f"--------   make {self.EHDres}-skin  --------")
			for file in skinfiles:
				if self.skinline_error:
					break
				if exists(file[2]):
					self.optionEHD(file[2], file[1])
				else:
					self.optionEHD(file[0], file[1])

			if self.skinline_error:
				print("--------   force HD-skin   --------")
				self.EHDenabled = False
				self.EHDfactor = 1
				self.EHDres = 'HD'
				self.EHDtxt = 'Standard HD'
				skinline_error = self.skinline_error
				self.skinline_error = False
				for file in skinfiles:
					if exists(file[2]):
						self.optionEHD(file[2], file[1])
					else:
						self.optionEHD(file[0], file[1])
				self.skinline_error = skinline_error
				self.updateIcons()
				self.makeGraphics(1)

			#remove *_TMP files
			for file in skinfiles:
				if exists(file[2]):
					remove(file[2])

			################
			# Buttons
			################

			if config.plugins.MyMetrixLiteOther.SkinDesignButtons.value:
				#backup
				for button in buttons:
					buttonfile = buttonpath[self.EHDres] + button[0]
					buttonbackupfile = buttonfile + '.backup'
					if exists(buttonfile) and not exists(buttonbackupfile):
						copy(buttonfile, buttonbackupfile)
					self.makeButtons(buttonfile, button[1], False)
				self.ButtonEffect = None
			else:
				#restore
				for button in buttons:
					buttonfile = buttonpath[self.EHDres] + button[0]
					buttonbackupfile = buttonfile + '.backup'
					if exists(buttonbackupfile):
						move(buttonbackupfile, buttonfile)

			################
			# info message
			################

			text = ""
			if self.skinline_error:
				self.getEHDSettings()
				self.ErrorCode = 5
				text += _("Error creating %s skin. HD skin is used!\n\n") % self.EHDres
				if not self.pixmap_error:
					text = text.rstrip('\n') + f"\n\n< {self.skinline_error} >\n\n"
				else:
					self.ErrorCode = 6
					text = text.rstrip('\n') + (_("\n(One or more %s icons are missing.)\n\n") + "< %s >\n\n") % (self.EHDres, self.pixmap_error)

			text += _("GUI needs a restart to apply a new skin.\nDo you want to Restart the GUI now?")

			if not self.ErrorCode:
				self.ErrorCode = 0
			if not self.silent:
				self.ErrorCode = 'reboot', text

		except Exception as error:
			print(f'[ActivateSkinSettings - applyChanges] {str(error)}')
			self.ErrorCode = 1
			if not self.silent:
				self.ErrorCode = 'error', _("Error creating Skin!") + f'\n< {error} >'
			#restore skinfiles
			if exists(SKIN_SOURCE + bname):
				move(SKIN_SOURCE + bname, SKIN_SOURCE)
			for file in skinfiles:
				if exists(file[1]):
					remove(file[1])
				if exists(file[2]):
					remove(file[2])
			#restore buttons
			for button in buttons:
				buttonfile = buttonpath["HD"] + button[0]
				buttonbackupfile = buttonfile + '.backup'
				if exists(buttonbackupfile):
					move(buttonbackupfile, buttonfile)
			#restore icons
			self.updateIcons()
			#restore default hd skin
			config.skin.primary_skin.setValue("MetrixHD/skin.xml")
		else:
			config.skin.primary_skin.setValue("MetrixHD/skin.MySkin.xml")
		config.skin.primary_skin.save()
		configfile.save()
		print(f"MyMetrixLite apply Changes - duration time: {round_half_up(time() - apply_starttime, 1)}s")

	def makeButtons(self, button, text, extern=True):
		try:
			#makeButtons
			if extern:
				self.getEHDSettings()

			sizex = int(80 * self.EHDfactor)
			sizey = int(40 * self.EHDfactor)
			framesize = config.plugins.MyMetrixLiteOther.SkinDesignButtonsFrameSize.value
			fonttyp = config.plugins.MyMetrixLiteOther.SkinDesignButtonsTextFont.value
			fontsize = int(config.plugins.MyMetrixLiteOther.SkinDesignButtonsTextSize.value * self.EHDfactor)

			color = config.plugins.MyMetrixLiteOther.SkinDesignButtonsFrameColor.value
			trans = config.plugins.MyMetrixLiteOther.SkinDesignButtonsFrameColorTransparency.value
			framecolor = rgba = (int(color[-6:][:2], 16), int(color[-4:][:2], 16), int(color[-2:][:2], 16), 255 - int(trans, 16))
			color = config.plugins.MyMetrixLiteOther.SkinDesignButtonsBackColor.value
			trans = config.plugins.MyMetrixLiteOther.SkinDesignButtonsBackColorTransparency.value
			backcolor = rgba = (int(color[-6:][:2], 16), int(color[-4:][:2], 16), int(color[-2:][:2], 16), 255 - int(trans, 16))
			color = config.plugins.MyMetrixLiteOther.SkinDesignButtonsTextColor.value
			trans = config.plugins.MyMetrixLiteOther.SkinDesignButtonsTextColorTransparency.value
			textcolor = rgba = (int(color[-6:][:2], 16), int(color[-4:][:2], 16), int(color[-2:][:2], 16), 255 - int(trans, 16))
			color = config.plugins.MyMetrixLiteOther.SkinDesignButtonsGlossyEffectColor.value
			trans = config.plugins.MyMetrixLiteOther.SkinDesignButtonsGlossyEffectIntensity.value
			glossycolor = rgba = (int(color[-6:][:2], 16), int(color[-4:][:2], 16), int(color[-2:][:2], 16), int(trans, 16))

			#symbols
			symbolpos = 0
			if 'key_leftright.png' in button or 'key_updown.png' in button:
				unicodechar = 'setrixHD' in config.plugins.MyMetrixLiteOther.SkinDesignButtonsTextFont.value or 'Raleway' in config.plugins.MyMetrixLiteOther.SkinDesignButtonsTextFont.value
				if unicodechar:
					symbolpos = -2
					fonttyp = '/usr/share/enigma2/MetrixHD/fonts/setrixHD.ttf'
					fontsize += int(fontsize / 2)
					if 'key_leftright.png' in button:
						text = u'\u02c2' + ' ' + u'\u02c3'
					else:
						text = u'\u02c4' + ' ' + u'\u02c5'
				else:
					symbolpos = 0
					fonttyp = '/usr/share/enigma2/MetrixHD/fonts/OpenSans-Regular.ttf'
					fontsize += int(fontsize / 2)
			else:
				text = f'{text}'
			#autoshrink text
			x = 0
			fontx = sizex + 1
			while fontx > sizex:
				font = ImageFont.truetype(fonttyp, fontsize - x)
				fontx, fonty = font.getsize(text)
				#fixme fonty size factor different with new pillow 6.2.1
				fonty = fonty * 1.27
				x += 1
			#frame
			img = Image.new("RGBA", (sizex, sizey), framecolor)
			draw = ImageDraw.Draw(img)
			#button
			draw.rectangle(((framesize, framesize), (sizex - framesize - 1, sizey - framesize - 1)), fill=backcolor)
			#text
			imgtxt = Image.new("RGBA", (sizex, sizey), (textcolor[0], textcolor[1], textcolor[2], 0))
			drawtxt = ImageDraw.Draw(imgtxt)
			drawtxt.text((int((sizex - fontx) / 2), int((sizey - fonty) / 2) + symbolpos + config.plugins.MyMetrixLiteOther.SkinDesignButtonsTextPosition.value), text, fill=textcolor, font=font)
			#rotate updown
			if 'key_updown.png' in button and not unicodechar:  # rotation disabled - if using unicode charachters
				top = int(font.getsize('<')[0] / 2) - 1
				lefta = int((sizex - fontx) / 2)
				righta = lefta + font.getsize('<')[0]
				leftb = lefta + fontx - font.getsize('<')[0]
				rightb = leftb + font.getsize('<')[0]
				upper = int((sizey - fonty + font.getsize('<')[1]) / 2) - top
				lower = upper + font.getsize('<')[0]
				imga = imgtxt.crop((lefta, upper, righta, lower)).rotate(-90)
				imgb = imgtxt.crop((leftb, upper, rightb, lower)).rotate(-90)
				drawtxt.rectangle(((0, 0), (sizex, sizey)), fill=(textcolor[0], textcolor[1], textcolor[2], 0))
				imgtxt.paste(imga, (lefta, top + 1))
				imgtxt.paste(imgb, (leftb, top + 1))
			#text under glossy
			if config.plugins.MyMetrixLiteOther.SkinDesignButtonsGlossyEffectOverText.value:
				img.paste(imgtxt, (0, 0), imgtxt)
			#glossy effect
			if config.plugins.MyMetrixLiteOther.SkinDesignButtonsGlossyEffect.value != 'no':
				if 'frame' in config.plugins.MyMetrixLiteOther.SkinDesignButtonsGlossyEffect.value:
					fs = 0
					sy = sizey
					sx = sizex
				else:
					fs = framesize
					sy = sizey - fs * 2
					sx = sizex - fs * 2
				if not self.ButtonEffect:
					a = glossycolor[3]
					esy = sy * float(config.plugins.MyMetrixLiteOther.SkinDesignButtonsGlossyEffectSize.value)
					if 'solid' in config.plugins.MyMetrixLiteOther.SkinDesignButtonsGlossyEffect.value:
						imga = Image.new("RGBA", (sizex - fs * 2, int(esy)), glossycolor)
					elif 'gradient' in config.plugins.MyMetrixLiteOther.SkinDesignButtonsGlossyEffect.value:
						imga = Image.new("RGBA", (sizex - fs * 2, int(esy)), (glossycolor[0], glossycolor[1], glossycolor[2], 0))
						draw = ImageDraw.Draw(imga)
						s = a / esy
						for ll in range(0, int(esy + 1)):
							draw.line([(0, ll), (sizex - fs * 2, ll)], fill=(glossycolor[0], glossycolor[1], glossycolor[2], int(a)))
							a -= s
					elif 'circle' in config.plugins.MyMetrixLiteOther.SkinDesignButtonsGlossyEffect.value:
						epx = sx * float(config.plugins.MyMetrixLiteOther.SkinDesignButtonsGlossyEffectPosX.value)
						epy = sy * float(config.plugins.MyMetrixLiteOther.SkinDesignButtonsGlossyEffectPosY.value)
						esx = sx * float(config.plugins.MyMetrixLiteOther.SkinDesignButtonsGlossyEffectSize.value)
						imga = Image.new("RGBA", (sx, sy))
						for y in range(sy):
							for x in range(sx):
								s = a * (float(sqrt((x - epx) ** 2 + (y - epy) ** 2)) / sqrt((esx ** 2) + (esy ** 2)))
								imga.putpixel((x, y), (glossycolor[0], glossycolor[1], glossycolor[2], a - int(s)))
					self.ButtonEffect = imga
				img.paste(self.ButtonEffect, (fs, fs), self.ButtonEffect)
			#text over glossy
			if not config.plugins.MyMetrixLiteOther.SkinDesignButtonsGlossyEffectOverText.value:
				img.paste(imgtxt, (0, 0), imgtxt)
			img.save(button)
			return 1
		except Exception:
			return 0

	def makeGraphics(self, factor):
		# epg
		color = self.makeNewColor(config.plugins.MyMetrixLiteColors.epgbackground.value, config.plugins.MyMetrixLiteColors.cologradient.value)
		cgfile = "/usr/share/enigma2/MetrixHD/colorgradient_bottom_epg.png"
		size = 220
		gpos = size - size * ((100 - int(config.plugins.MyMetrixLiteColors.cologradient_position.value)) * 0.01)
		gsize = (size - gpos) * (int(config.plugins.MyMetrixLiteColors.cologradient_size.value) * 0.01)
		if color:
			self.makeColorGradient(cgfile, int(1280 * factor), int(size * factor), color, int(gpos * factor), int(gsize * factor), 'up')
		else:
			if isfile(cgfile):
				remove(cgfile)
		# ib
		color = self.makeNewColor(config.plugins.MyMetrixLiteColors.infobarbackground.value, config.plugins.MyMetrixLiteColors.cologradient.value)
		cgfile = "/usr/share/enigma2/MetrixHD/colorgradient_bottom_ib.png"
		size = 160
		gpos = size - size * ((100 - int(config.plugins.MyMetrixLiteColors.cologradient_position.value)) * 0.01)
		gsize = (size - gpos) * (int(config.plugins.MyMetrixLiteColors.cologradient_size.value) * 0.01)
		if color:
			self.makeColorGradient(cgfile, int(1280 * factor), int(size * factor), color, int(gpos * factor), int(gsize * factor), 'up')
		else:
			if isfile(cgfile):
				remove(cgfile)
		cgfile = "/usr/share/enigma2/MetrixHD/colorgradient_top_ib.png"
		size = 30
		gpos = size - size * ((100 - int(config.plugins.MyMetrixLiteColors.cologradient_position.value)) * 0.01)
		gsize = (size - gpos) * (int(config.plugins.MyMetrixLiteColors.cologradient_size.value) * 0.01)
		if color:
			self.makeColorGradient(cgfile, int(1280 * factor), int(size * factor), color, int(gpos * factor), int(gsize * factor), 'down')
		else:
			if isfile(cgfile):
				remove(cgfile)
		# mb
		color = self.makeNewColor(config.plugins.MyMetrixLiteColors.infobarbackground.value, config.plugins.MyMetrixLiteColors.cologradient.value)
		cgfile = "/usr/share/enigma2/MetrixHD/colorgradient_bottom_mb.png"
		if int(config.plugins.MyMetrixLiteOther.InfoBarMoviePlayerDesign.value) > 2:
			size = 80
		else:
			size = 150
		gpos = size - size * ((100 - int(config.plugins.MyMetrixLiteColors.cologradient_position.value)) * 0.01)
		gsize = (size - gpos) * (int(config.plugins.MyMetrixLiteColors.cologradient_size.value) * 0.01)
		if color:
			self.makeColorGradient(cgfile, int(1280 * factor), int(150 * factor), color, int(gpos * factor), int(gsize * factor), 'up')
		else:
			if isfile(cgfile):
				remove(cgfile)
		# db
		color = self.makeNewColor(config.plugins.MyMetrixLiteColors.infobarbackground.value, config.plugins.MyMetrixLiteColors.cologradient.value)
		cgfile = "/usr/share/enigma2/MetrixHD/colorgradient_bottom_pb.png"
		size = 80
		gpos = size - size * ((100 - int(config.plugins.MyMetrixLiteColors.cologradient_position.value)) * 0.01)
		gsize = (size - gpos) * (int(config.plugins.MyMetrixLiteColors.cologradient_size.value) * 0.01)
		if color:
			self.makeColorGradient(cgfile, int(1280 * factor), int(size * factor), color, int(gpos * factor), int(gsize * factor), 'up')
		else:
			if isfile(cgfile):
				remove(cgfile)
		# layer a
		color = self.makeNewColor(config.plugins.MyMetrixLiteColors.layerabackground.value, config.plugins.MyMetrixLiteColors.cologradient.value)
		cgfile = "/usr/share/enigma2/MetrixHD/colorgradient_top_qm.png"
		size = 95
		gpos = size - size * ((100 - int(config.plugins.MyMetrixLiteColors.cologradient_position.value)) * 0.01)
		gsize = (size - gpos) * (int(config.plugins.MyMetrixLiteColors.cologradient_size.value) * 0.01)
		if color:
			self.makeColorGradient(cgfile, int(1280 * factor), int(size * factor), color, int(gpos * factor), int(gsize * factor), 'down')
		else:
			if isfile(cgfile):
				remove(cgfile)
		# ibts background
		color = config.plugins.MyMetrixLiteColors.layerabackground.value
		alpha = config.plugins.MyMetrixLiteColors.layerabackgroundtransparency.value
		cgfile = "/usr/share/enigma2/MetrixHD/ibts/background.png"
		if isdir("/usr/share/enigma2/MetrixHD/ibts"):
			self.makeColorField(cgfile, int(1280 * factor), int(32 * factor), color, alpha)
		# file commander image viewer background
		color = config.plugins.MyMetrixLiteColors.layerabackground.value
		cgfile = "/usr/share/enigma2/MetrixHD/colorgradient_imageviewer.png"
		self.makeColorGradient(cgfile, int(30 * factor), int(640 * factor), color, 0, int(640 * factor), 'right', 255, 0)

	def makeNewColor(self, color, coloroption):
		if coloroption == '0':
			return None
		elif coloroption == '1':
			return color
		elif len(coloroption) < 6:  # modify current color
			coloroption = int(coloroption)
			r = int(color[-6:][:2], 16)
			r -= r * 0.01 * int(coloroption)
			g = int(color[-4:][:2], 16)
			g -= g * 0.01 * int(coloroption)
			b = int(color[-2:][:2], 16)
			b -= b * 0.01 * int(coloroption)
			if r < 0:
				r = 0
			if g < 0:
				g = 0
			if b < 0:
				b = 0
			return f"{int(r):02x}{int(g):02x}{int(b):02x}"
		elif len(coloroption) == 6:
			return coloroption
		else:
			return color

	def makeColorGradient(self, name, sizex, sizey, color, begin, height, direction, alphaA=None, alphaB=None):
		#print name
		if alphaA is None:
			alphaA = 255 - int(config.plugins.MyMetrixLiteColors.cologradient_transparencyA.value, 16)
		if alphaB is None:
			alphaB = 255 - int(config.plugins.MyMetrixLiteColors.cologradient_transparencyB.value, 16)
		rgba = (int(color[-6:][:2], 16), int(color[-4:][:2], 16), int(color[-2:][:2], 16), 0)
		imga = Image.new("RGBA", (sizex, sizey), rgba)
		rgba = (int(color[-6:][:2], 16), int(color[-4:][:2], 16), int(color[-2:][:2], 16), alphaA)
		imgb = Image.new("RGBA", (sizex, begin), rgba)
		imgc = Image.new("RGBA", (sizex, height), rgba)
		gradient = Image.new('L', (1, alphaA - alphaB + 1))
		for y in range(0, alphaA - alphaB + 1):
			gradient.putpixel((0, y), alphaB + y)
		gradient = gradient.resize(imgc.size)
		imgc.putalpha(gradient)
		imga.paste(imgb, (0, imga.size[1] - begin))
		imga.paste(imgc, (0, imga.size[1] - begin - height))
		if direction == 'up':
			pass
		elif direction == 'left':
			imga = imga.transpose(Image.ROTATE_90)
		elif direction == 'down':
			imga = imga.transpose(Image.ROTATE_180)
		elif direction == 'right':
			imga = imga.transpose(Image.ROTATE_270)
		imga.save(name)

	def makeColorField(self, name, sizex, sizey, color, alpha):
		rgba = (int(color[-6:][:2], 16), int(color[-4:][:2], 16), int(color[-2:][:2], 16), 255 - int(alpha, 16))
		imga = Image.new("RGBA", (sizex, sizey), rgba)
		imga.save(name)

	def updateIcons(self, target="HD"):
		# backward compatibility - remove old icon files ---------------------------
		dpathlist = ["/usr/share/enigma2/MetrixHD/",
					"/usr/share/enigma2/MetrixHD/skin_default/buttons/",
					"/usr/share/enigma2/MetrixHD/skin_default/icons/",
					"/usr/share/enigma2/MetrixHD/icons/",
					"/usr/share/enigma2/MetrixHD/buttons/",
					"/usr/share/enigma2/MetrixHD/extensions/",
					"/usr/lib/enigma2/python/Plugins/SystemPlugins/SoftwareManager/",
					"/usr/lib/enigma2/python/Plugins/SystemPlugins/AutoBouquetsMaker/images/",
					"/usr/lib/enigma2/python/Plugins/SystemPlugins/NetworkBrowser/icons/",
					"/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/",
					"/usr/share/enigma2/MetrixHD/ibts/",
					"/usr/share/enigma2/MetrixHD/emc/"]
		for dpath in dpathlist:
			if isdir(dpath):
				for file in listdir(dpath):
					if file.endswith('.png.hd') and isfile(dpath + file):
						move(dpath + file, dpath + file[:-3])
					elif file.endswith('.png.del') and isfile(dpath + file):
						remove(dpath + file)
					elif dpath == "/usr/share/enigma2/MetrixHD/" and file.startswith("skin_00") and isfile(dpath + file):
						remove(dpath + file)
		dpath = "/usr/lib/enigma2/python/Plugins/Extensions/MyMetrixLite/images/"
		npath = "/usr/lib/enigma2/python/Plugins/Extensions/MyMetrixLite/images_hd/"
		if isdir(dpath) and isdir(npath):
			rmtree(dpath)
			rename(npath, dpath)
		# --------------------------------------------------------------------------

		spath = f'/usr/share/enigma2/MetrixHD/{target}'
		dpath = '/usr/share/enigma2/MetrixHD'

		# first reset / set hd icons
		if not isdir(dpath):
			return
		for x in listdir(dpath):
			dest = pathjoin(dpath, x)
			if islink(dest):
				unlink(dest)
		for x in listdir(dpath):
			src = pathjoin(dpath, x)
			dest = pathjoin(dpath, x[1:-3])
			if x.startswith('.') and x.endswith('_hd') and not exists(dest):
				rename(src, dest)

		# set other res icons
		if target == "HD" or not isdir(spath):
			return
		for x in listdir(spath):
			if x == "Plugins":  # folder is current placeholder for unused icons
				continue
			src = pathjoin(spath, x)
			dest = pathjoin(dpath, x)
			hd = pathjoin(dpath, '.' + x + '_hd')
			if x == 'emc' and int(config.plugins.MyMetrixLiteOther.showEMCSelectionRows.value) > 3:
				if target == 'FHD':
					continue
				elif target == 'UHD' and isdir('/usr/share/enigma2/MetrixHD/FHD/emc'):
					src = '/usr/share/enigma2/MetrixHD/FHD/emc'
			if exists(dest) and not exists(hd):
				rename(dest, hd)
			try:
				symlink(src, dest)
			except OSError as e:
				raise Exception(_("Can't create symlink:") + f"\n{src}\n---> {dest}\n({e})")

	def optionEHD(self, sourceFile, targetFile):
		# oldlinechanger = config.plugins.MyMetrixLiteOther.EHDoldlinechanger.value

		run_mod = False
		next_rename = False
		next_picon_zoom = False
		next_pixmap_ignore = False
		line_disabled = False

		self.xpos = 0
		self.ypos = 0

		starttime = datetime.now()
		print("starting   " + sourceFile + "   --->   " + targetFile)

		f = open(sourceFile, "r")
		f1 = open(targetFile, "w")

		i = 0
		i_save = i
		sb_width = config.plugins.MyMetrixLiteOther.SkinDesignScrollbarSliderWidth.value + config.plugins.MyMetrixLiteOther.SkinDesignScrollbarBorderWidth.value * 2
		sb_bwidth = config.plugins.MyMetrixLiteOther.SkinDesignScrollbarBorderWidth.value
		for line in f.readlines():
			i += 1
#options for all skin files
			if sb_width != 10:
				line = line.replace('scrollbarWidth="10"', f'scrollbarWidth="{sb_width}"')
			if sb_bwidth != 1:
				line = line.replace('scrollbarSliderBorderWidth="1"', f'scrollbarSliderBorderWidth="{sb_bwidth}"')
				line = line.replace('scrollbarBorderWidth="1"', f'scrollbarBorderWidth="{sb_bwidth}"')
			if config.plugins.MyMetrixLiteColors.backgroundtextborderwidth.value and ' font="global_large' in line and ' borderWidth=' not in line and ' borderColor=' not in line:
				line = line.replace(' font=', f' borderWidth="{config.plugins.MyMetrixLiteColors.backgroundtextborderwidth.value}" borderColor="#{config.plugins.MyMetrixLiteColors.backgroundtextbordertransparency.value}{config.plugins.MyMetrixLiteColors.backgroundtextbordercolor.value}" font=')
			if not config.plugins.MyMetrixLiteOther.SkinDesignMenuScrollInfo.value and 'name="menu_next_side_marker"' in line:
				line = line.replace('text="&#x25ba;"', 'text=""')
			if config.plugins.MyMetrixLiteOther.emc_pig.value:
				if 'screen name="EMCSelection_PIG"' in line:
					line = line.replace('screen name="EMCSelection_PIG"', 'screen name="EMCSelection"')
				elif 'screen name="EMCSelection"' in line:
					line = line.replace('screen name="EMCSelection"', 'screen name="EMCSelection_noPIG"')
			if config.plugins.MyMetrixLiteOther.movielist_pig.value:
				if 'screen name="MovieSelection_PIG"' in line:
					line = line.replace('screen name="MovieSelection_PIG"', 'screen name="MovieSelection"')
				elif 'screen name="MovieSelection"' in line:
					line = line.replace('screen name="MovieSelection"', 'screen name="MovieSelection_noPIG"')
			if not config.plugins.MyMetrixLiteColors.cologradient_show_background.value and 'name="GRADIENT_BACKGROUND"' in line:
				continue
			#list margin channellist
			line = line.replace('listMarginRight="5"', f'listMarginRight="{sb_width + int(5 * self.EHDfactor) + 5 if config.plugins.MyMetrixLiteOther.showChannelListScrollbar.value else int(5 * self.EHDfactor)}"')
			line = line.replace('listMarginLeft="5"', f'listMarginLeft="{int(5 * self.EHDfactor)}"')
			#-----------------------
#options for all skin files end
			if self.EHDenabled:
				try:
#rename flag
					if '<!-- cf#_#rename -->' in line:
						next_rename = True
						run_mod = False
					else:
						if next_rename:
							if '#_' + self.EHDres + 'screen' in line:
								line = line.replace(f'#_{self.EHDres}screen', "")
							elif 'name="' in line and '#_' not in line and 'HDscreen' not in line:
									line = sub(r'(name=")(\w+)', r'\1\2#_HDscreen', line)
							next_rename = False
#control flags
						if '<!-- cf#_#begin -->' in line or '<!-- cf#_#start -->' in line:
							run_mod = True
						elif '<!-- cf#_#stop -->' in line:
							run_mod = False
#picon zoom, pixmap ignore flags
						if '<!-- cf#_#picon -->' in line and self.picon_zoom != self.EHDfactor:
							#only for next line!
							i_save = i + 1
							next_picon_zoom = True
						elif '<!-- cf#_#pixnore -->' in line:
							#only for next line!
							i_save = i + 1
							next_pixmap_ignore = True
						else:
							if (next_picon_zoom or next_pixmap_ignore) and i > i_save:
								self.xpos = 0
								self.ypos = 0
								next_picon_zoom = False
								next_pixmap_ignore = False
#line disabled on
					if 'cf#_#' not in line and match('<!--|#+', line.lstrip()):
						#print 'line disabled on', i, line
						line_disabled = True
#test pixmap path
					if not line_disabled and not next_pixmap_ignore and 'MetrixHD/' in line and '.png' in line:
						pics = findall(r'Metrix[-/\w]+.png', line)
						for pic in pics:
							if not pic.startswith('/usr/share/enigma2/'):
								pic = '/usr/share/enigma2/' + pic
							if not isfile(pic):
								pic = realpath(pic)
								print(f"pixmap missing - line:{i} / {pic}")
								self.pixmap_error = pic
								self.skinline_error = True
								break
					if run_mod and not line_disabled and not self.skinline_error:
#						if oldlinechanger:
#							line = self.linerchanger_old(line, next_picon_zoom)
#						else:
						line = self.linerchanger_new(line, next_picon_zoom, "skin.MySkin.xml" in sourceFile)
#line disabled off
					if line_disabled and 'cf#_#' not in line and (match('#+', line.lstrip()) or match('.*-->.*', line.rstrip())):
						#print 'line disabled off', i, line
						line_disabled = False
				except Exception as error:
					self.skinline_error = error
					import traceback
					traceback.print_exc()
					print(f"error in line: {i} / {str(error)}\n{line}\n--------")
			f1.write(line)
			if self.skinline_error:
				break
		f.close()
		f1.close()
		if not self.skinline_error:
			print(f"complete in: {datetime.now() - starttime}")
			print("--------")

	def linereplacer(self, m):
		#print m.groups()
		ret = list(m.groups())
		if ret[0].startswith('name="underline"'):
			ulsize = config.plugins.MyMetrixLiteOther.layeraunderlinesize.value
			ulposy = config.plugins.MyMetrixLiteOther.layeraunderlineposy.value
			ret[3] = str(int(ret[3]) - ulsize // 2 + ulposy)
			ret[7] = str(ulsize)
			return ''.join(ret)
		i = 0
		for x in ret:
			if match('[0-9]\d{%d,}' % (len(x) - 1), x):
				if ret[0].startswith('size="') and (self.xpos or self.ypos):
					x = int(round_half_up(int(x) * self.picon_zoom, self.round_par))
				else:
					x = int(round_half_up(int(x) * self.EHDfactor, self.round_par))
				if ret[0].startswith('position="') and (self.xpos or self.ypos):
					if i == 1:
						x += self.xpos
					else:
						x += self.ypos
				elif 'font' in ret[0].lower() or ('value=' in ret[0] and i == 3 and ';' in ret[2]):
					x += self.font_offset
				ret[i] = str(x)
			i += 1
		return ''.join(ret)

	def linerchanger_new(self, line, next_picon_zoom, rootFile):  # with regex
#<resolution xres="1280" yres="720"
		if rootFile:
			if '<resolution ' in line:
				return sub(r'(xres=")(\d+)(" *yres=")(\d+)', self.linereplacer, line)
#<parameter name="AutotimerEnabledIcon" value="6,2,24,25"
#<parameter name="ServiceInfoFont" value="screen_text;20"/>
			if '<parameter name="' in line and 'value="' in line:
#<parameter name="ChoicelistVerticalAlignment" value="*center" />
				if 'value="*' in line:
					return line
				return sub(r'(value=")(\d+|\w+)([,;"])(\d*)([,"]*)(\d*)([,"]*)(\d*)([,"]*)(\d*)([,"]*)(\d*)([,"]*)(\d*)([,"]*)(\d*)([,"]*)(\d*)([,"]*)(\d*)("*)', self.linereplacer, line)  # prepared for max 10 values
#size="200,100"
#size = (500, 45)
		if ('size="' in line and 'alias name="' not in line) or ('size' in line and '(' in line and ')' in line):
			if next_picon_zoom:
				pos = findall(r'(?<= size=")([\w]*[+-]*)(\d*),([\w]*[+-]*)(\d*)', line)
				if pos:
					xpos = int(pos[0][0] + pos[0][1]) if not match('[ce]', pos[0][0]) else pos[0][1] if pos[0][1] else 0
					ypos = int(pos[0][2] + pos[0][3]) if not match('[ce]', pos[0][2]) else pos[0][3] if pos[0][3] else 0
					self.xpos = int(round_half_up((xpos * self.EHDfactor - xpos * self.picon_zoom) / 2.0, self.round_par)) if xpos else 0
					self.ypos = int(round_half_up((ypos * self.EHDfactor - ypos * self.picon_zoom) / 2.0, self.round_par)) if ypos else 0
			line = sub(r'(size *= *["(][ ce+-]*)(\d*)( *, *)([ ce+-]+|\d+)(\d+|[")]*)', self.linereplacer, line)
#position="423,460"
#(pos = (40, 5)
		if 'position="' in line or ('(pos' in line and ')' in line):
			line = sub(r'(pos[ition]* *= *["(][ center+-]*)(\d*)( *, *)([ center+-]+|\d+)(\d+|[")]*)', self.linereplacer, line)
#font="Regular;20"
#Font="Regular;20"
#ServiceFontGraphical="epg_text;20" EntryFontGraphical="epg_text;20"
#ServiceFontInfobar="epg_text;20" EntryFontInfobar="epg_text;20"
#EventFontSingle="epg_event;22"
#EventFontMulti="epg_event;22"
#TimeFontVertical="epg_event;22" EventFontVertical="epg_event;18"
#CoolFont="epg_text;20" CoolSelectFont="epg_text;20" CoolDateFont="epg_text;30"
#CoolFont="Regular;19" CoolServiceFont="Regular;19" CoolEventFont="Regular;19"
		if ('font' in line or 'Font' in line) and 'alias name="' not in line:
			line = sub(r'(\w*[Ff]ont\w*=" *)(\w+; *)(\d+)', self.linereplacer, line)
#<alias name="Body" font="screen_text" size="20" height="25" />
		if 'font="' in line and 'alias name="' in line:
			line = sub(r'(font="\w+" +size=" *)(\d+)(" *height=" *|)(\d*)', self.linereplacer, line)
#"fonts": [gFont("Regular",18),gFont("Regular",14),gFont("Regular",24),gFont("Regular",20)]
		if '"fonts":' in line and 'gFont' in line:
			line = sub(r'(gFont[(]"\w+", *)(\d+)', self.linereplacer, line)
#offset="5,0"
		if ' offset="' in line or 'shadowOffset="' in line:
			line = sub(r'([shadow]*[Oo]ffset=")(\d+)(,)(\d+)', self.linereplacer, line)
#rowSplit="25"
#rowSplit1="25"
#rowSplit2="25"
#rowHeight="25"
#satPosLeft="160"
#iconMargin="5"
#fieldMargins="10"
#itemsDistances="10"
#progressbarHeight="10"
#progressBarWidth="50"
#progressbarBorderWidth="1" -> deactivated
#itemHeight="25"
#"itemHeight": 45
#": (90,[
		if 'rowSplit' in line or 'rowHeight="' in line or 'satPosLeft="' in line or 'iconMargin="' in line or 'fieldMargins="' in line or 'itemsDistances="' in line or 'progressbarHeight="' in line or 'progressBarWidth="' in line or 'itemHeight="' in line or '"itemHeight":' in line or 'itemWidth="' in line or '"itemWidth":' in line or ('": (' in line and '[' in line):
			line = sub(r'([iconfeld]+Margin[s]*=" *|itemsDistances="|progress[Bb]ar[HeightWd]+=" *|"*itemHeight[=":]+ *|"*itemWidth[=":]+ *|": *[(]|row[HeightSpl]+\d*=" *|satPosLeft=" *)(\d+)', self.linereplacer, line)
#messagebox start
#offset_listposx = 10
#offset_listposy = 10
#offset_listwidth = 10
#offset_listheight = 30
#offset_textwidth = 20
#offset_textheight = 90
#min_width = 400
#min_height = 50
#offset = 21
		if 'offset_listposx =' in line or 'offset_listposy =' in line or 'offset_listwidth =' in line or 'offset_listheight =' in line or 'offset_textwidth =' in line or 'offset_textheight =' in line or 'min_width =' in line or 'min_height =' in line or 'offset =' in line:
			line = sub(r'(offset_*\w* *= *|min_\w+ *= *)(\d+)', self.linereplacer, line)
#messagebox end
#emc special start
#CoolSelNumTxtWidth="26"
#CoolDateHPos="1"
#CoolProgressHPos="1"
#CoolMovieHPos="1"
#CoolDirInfoWidth="110"
#CoolCSWidth="110"
#CoolProgressPos="35"
#CoolIconPos="35"
#CoolIconHPos="35"
#CoolBarPos="35"
#CoolBarHPos="10"
#CoolMoviePos="110"
#CoolDatePos="590"
#CoolCSPos"590"
#CoolMovieSize="490"
#CoolFolderSize="490"
#CoolDateWidth="110"
#CoolPiconPos="100"
#CoolPiconHPos="2"
#CoolPiconWidth="60"
#CoolPiconHeight="26"
#CoolMoviePiconPos="160"
#CoolMoviePiconSize="425"
#CoolIconSize="24,24"
#CoolBarSize="65,10"
#CoolBarSizeSa="65,10"
#/CoolPointerRec.png:980,0"
#/CoolPointerRec2.png:1080,0"
		if 'widget name="list"' in line and ' Cool' in line and ' CoolEvent' not in line or 'render="PositionGauge"' in line:
			line = sub(r'(Cool\w+=" *|Cool\w+.png: *)(\d+)([,"])(\d+|)', self.linereplacer, line)
#emc special end
#cool tv guide special start
#CoolServiceSize="220"
#CoolEventSize="720"
#CoolServicePos="4"
#CoolServiceHPos="1"
#CoolEventPos="355"
#CoolEventHPos="1"
#CoolBarPos="240"
#CoolBarHPos="10"
#CoolTimePos="225"
#CoolTimeHPos="2"
#CoolBarSize="100"
#CoolBarHigh="10"
#CoolTimeSize="120"
#CoolDurationPos="1055"
#CoolDurationSize="100"
#CoolPico="35"
#CoolDaySize="100"
#CoolDayPos="0"
#CoolDayHPos="2"
#CoolDatePos="0"
#CoolDateHPos="0"
#CoolDateSize="0"
#CoolMarkerHPos="200"
#CoolMarkerPicPos="2"
#CoolMarkerPicHPos="2"
#CoolPicoPos="2"
#CoolPicoHPos="2"
		if ('widget name="list"' in line or 'widget name="CoolEvent"' in line) and ' CoolEvent' in line:
			line = sub(r'(Cool\w+=" *)(\d+)', self.linereplacer, line)
#cool tv guide special end

#colPosition="240"
		if ' colPosition="' in line:
			line = sub(r'(colPosition=" *)(\d+)', self.linereplacer, line)

#itemSpacing="10,10"
		if ' itemSpacing="' in line:
			line = sub(r'(itemSpacing=")(\d+)(,)(\d+)', self.linereplacer, line)

		return line

	def linerchanger_old(self, line, next_picon_zoom):  # faster than with regex :(
		r_par = self.round_par
		f_offset = self.font_offset
		FACT = self.EHDfactor
		PFACT = self.picon_zoom

#<resolution xres="1280" yres="720"
		if '<resolution ' in line:
			n1 = line.find('xres', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', (n2 + 1))
			line = line[:(n2 + 1)] + "1920" + line[(n3):]

			n1 = line.find('yres', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', (n2 + 1))
			line = line[:(n2 + 1)] + "1080" + line[(n3):]
#<parameter name="AutotimerEnabledIcon" value="6,2,24,25"
		# ignore colors
		if '<parameter name="' in line and 'value="0x00' in line:
			return line

#<parameter name="ChoicelistVerticalAlignment" value="*center" />
		if '<parameter name="' in line and 'value="*' in line:
			return line

		if '<parameter name="' in line and 'value="' in line:
			n1 = line.find('value="', 0)
			n2 = line.find('"', n1)
			n12 = line.find('"', n2 + 1)
			if 'Font' in line:
				parcount = len(line[n2:n12 + 1].split(';'))
			else:
				parcount = len(line[n2:n12 + 1].split(','))
			strnew = ""
			if parcount == 1:
				p1 = int(round_half_up(float(int(line[(n2 + 1):n12]) * FACT), r_par))
				strnew = f'value="{p1}"'
			elif parcount == 2:
				if 'Font' in line:
					n3 = line.find(';', n2)
					p1 = line[(n2 + 1):n3]
					p2 = int(f_offset + round_half_up(float(int(line[(n3 + 1):n12]) * FACT), r_par))
					strnew = f'value="{p1};{p2}"'
				else:
					n3 = line.find(',', n2)
					p1 = int(round_half_up(float(int(line[(n2 + 1):n3]) * FACT), r_par))
					p2 = int(round_half_up(float(int(line[(n3 + 1):n12]) * FACT), r_par))
					strnew = f'value="{p1},{p2}"'
			elif parcount == 3:
				n3 = line.find(',', n2)
				n4 = line.find(',', n3 + 1)
				p1 = int(round_half_up(float(int(line[(n2 + 1):n3]) * FACT), r_par))
				p2 = int(round_half_up(float(int(line[(n3 + 1):n4]) * FACT), r_par))
				p3 = int(round_half_up(float(int(line[(n4 + 1):n12]) * FACT), r_par))
				strnew = f'value="{p1},{p2},{p3}"'
			elif parcount == 4:
				n3 = line.find(',', n2)
				n4 = line.find(',', n3 + 1)
				n5 = line.find(',', n4 + 1)
				p1 = int(round_half_up(float(int(line[(n2 + 1):n3]) * FACT), r_par))
				p2 = int(round_half_up(float(int(line[(n3 + 1):n4]) * FACT), r_par))
				p3 = int(round_half_up(float(int(line[(n4 + 1):n5]) * FACT), r_par))
				p4 = int(round_half_up(float(int(line[(n5 + 1):n12]) * FACT), r_par))
				strnew = f'value="{p1},{p2},{p3},{p4}"'
			elif parcount == 5:
				n3 = line.find(',', n2)
				n4 = line.find(',', n3 + 1)
				n5 = line.find(',', n4 + 1)
				n6 = line.find(',', n5 + 1)
				p1 = int(round_half_up(float(int(line[(n2 + 1):n3]) * FACT), r_par))
				p2 = int(round_half_up(float(int(line[(n3 + 1):n4]) * FACT), r_par))
				p3 = int(round_half_up(float(int(line[(n4 + 1):n5]) * FACT), r_par))
				p4 = int(round_half_up(float(int(line[(n5 + 1):n6]) * FACT), r_par))
				p5 = int(round_half_up(float(int(line[(n6 + 1):n12]) * FACT), r_par))
				strnew = f'value="{p1},{p2},{p3},{p4},{p5}"'
			elif parcount == 6:
				n3 = line.find(',', n2)
				n4 = line.find(',', n3 + 1)
				n5 = line.find(',', n4 + 1)
				n6 = line.find(',', n5 + 1)
				n7 = line.find(',', n6 + 1)
				p1 = int(round_half_up(float(int(line[(n2 + 1):n3]) * FACT), r_par))
				p2 = int(round_half_up(float(int(line[(n3 + 1):n4]) * FACT), r_par))
				p3 = int(round_half_up(float(int(line[(n4 + 1):n5]) * FACT), r_par))
				p4 = int(round_half_up(float(int(line[(n5 + 1):n6]) * FACT), r_par))
				p5 = int(round_half_up(float(int(line[(n6 + 1):n7]) * FACT), r_par))
				p6 = int(round_half_up(float(int(line[(n7 + 1):n12]) * FACT), r_par))
				strnew = f'value="{p1},{p2},{p3},{p4},{p5},{p6}"'
			elif parcount == 7:
				n3 = line.find(',', n2)
				n4 = line.find(',', n3 + 1)
				n5 = line.find(',', n4 + 1)
				n6 = line.find(',', n5 + 1)
				n7 = line.find(',', n6 + 1)
				n8 = line.find(',', n7 + 1)
				p1 = int(round_half_up(float(int(line[(n2 + 1):n3]) * FACT), r_par))
				p2 = int(round_half_up(float(int(line[(n3 + 1):n4]) * FACT), r_par))
				p3 = int(round_half_up(float(int(line[(n4 + 1):n5]) * FACT), r_par))
				p4 = int(round_half_up(float(int(line[(n5 + 1):n6]) * FACT), r_par))
				p5 = int(round_half_up(float(int(line[(n6 + 1):n7]) * FACT), r_par))
				p6 = int(round_half_up(float(int(line[(n7 + 1):n8]) * FACT), r_par))
				p7 = int(round_half_up(float(int(line[(n8 + 1):n12]) * FACT), r_par))
				strnew = f'value="{p1},{p2},{p3},{p4},{p5},{p6},{p7}"'
			elif parcount == 8:
				n3 = line.find(',', n2)
				n4 = line.find(',', n3 + 1)
				n5 = line.find(',', n4 + 1)
				n6 = line.find(',', n5 + 1)
				n7 = line.find(',', n6 + 1)
				n8 = line.find(',', n7 + 1)
				n9 = line.find(',', n8 + 1)
				p1 = int(round_half_up(float(int(line[(n2 + 1):n3]) * FACT), r_par))
				p2 = int(round_half_up(float(int(line[(n3 + 1):n4]) * FACT), r_par))
				p3 = int(round_half_up(float(int(line[(n4 + 1):n5]) * FACT), r_par))
				p4 = int(round_half_up(float(int(line[(n5 + 1):n6]) * FACT), r_par))
				p5 = int(round_half_up(float(int(line[(n6 + 1):n7]) * FACT), r_par))
				p6 = int(round_half_up(float(int(line[(n7 + 1):n8]) * FACT), r_par))
				p7 = int(round_half_up(float(int(line[(n8 + 1):n9]) * FACT), r_par))
				p8 = int(round_half_up(float(int(line[(n9 + 1):n12]) * FACT), r_par))
				strnew = f'value="{p1},{p2},{p3},{p4},{p5},{p6},{p7},{p8}"'

			if strnew:
				line = line[:n1] + strnew + line[(n12 + 1):]
#rowSplit="25"
		if 'rowSplit' in line:
			s = 0
			n3 = 0
			for s in range(0, line.count('rowSplit')):
				n1 = line.find('rowSplit', n3)
				n2 = line.find('="', n1)
				n3 = line.find('"', n2 + 2)
				y = line[(n2 + 2):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 2] + ynew
				line = line[:n1] + strnew + line[n3:]
#rowHeight="25"
		if 'rowHeight="' in line:
			n1 = line.find('rowHeight="', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', n2 + 1)
			y = line[(n2 + 1):n3]

			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + ynew + '"'
			line = line[:n1] + strnew + line[(n3 + 1):]
#satPosLeft="160"
		if 'satPosLeft="' in line:
			n1 = line.find('satPosLeft="', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', n2 + 1)
			y = line[(n2 + 1):n3]

			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + ynew + '"'
			line = line[:n1] + strnew + line[(n3 + 1):]

#iconMargin="5"
		if 'iconMargin="' in line:
			n1 = line.find('iconMargin="', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', n2 + 1)
			y = line[(n2 + 1):n3]

			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + ynew + '"'
			line = line[:n1] + strnew + line[(n3 + 1):]
#size="200,100"
		xpos = 0
		ypos = 0
		if 'size="' in line and 'alias name="' not in line:
			n1 = line.find('size="', 0)
			n2 = line.find('"', n1)
			n3 = line.find(',', n2)
			n4 = line.find('"', n3)
			x = line[(n2 + 1):n3]
			y = line[(n3 + 1):n4]
			if "c+" in x:
				x1 = x.replace("c+", "")
				xpos = int(round_half_up(float((int(x1) * FACT - int(x1) * PFACT) / 2), r_par))
				x1new = str(int(round_half_up(float(int(x1) * PFACT), r_par)))
				xnew = "c+" + x1new
			elif "c-" in x:
				x1 = x.replace("c-", "")
				xpos = int(round_half_up(float((int(x1) * FACT - int(x1) * PFACT) / 2), r_par))
				x1new = str(int(round_half_up(float(int(x1) * PFACT), r_par)))
				xnew = "c-" + x1new
			elif "e-" in x:
				x1 = x.replace("e-", "")
				xpos = int(round_half_up(float((int(x1) * FACT - int(x1) * PFACT) / 2), r_par))
				x1new = str(int(round_half_up(float(int(x1) * PFACT), r_par)))
				xnew = "e-" + x1new
			else:
				xpos = int(round_half_up(float((int(x) * FACT - int(x) * PFACT) / 2), r_par))
				xnew = str(int(round_half_up(float(int(x) * PFACT), r_par)))

			if "c+" in y:
				y1 = y.replace("c+", "")
				ypos = int(round_half_up(float((int(y1) * FACT - int(y1) * PFACT) / 2), r_par))
				y1new = str(int(round_half_up(float(int(y1) * PFACT), r_par)))
				ynew = "c+" + y1new
			elif "c-" in y:
				y1 = y.replace("c-", "")
				ypos = int(round_half_up(float((int(y1) * FACT - int(y1) * PFACT) / 2), r_par))
				y1new = str(int(round_half_up(float(int(y1) * PFACT), r_par)))
				ynew = "c-" + y1new
			elif "e-" in y:
				y1 = y.replace("e-", "")
				ypos = int(round_half_up(float((int(y1) * FACT - int(y1) * PFACT) / 2), r_par))
				y1new = str(int(round_half_up(float(int(y1) * PFACT), r_par)))
				ynew = "e-" + y1new
			else:
				ypos = int(round_half_up(float((int(y) * FACT - int(y) * PFACT) / 2), r_par))
				ynew = str(int(round_half_up(float(int(y) * PFACT), r_par)))

			strnew = 'size="' + xnew + ',' + ynew + '"'
			line = line[:n1] + strnew + line[(n4 + 1):]
#position="423,460"
		if not next_picon_zoom:
			xpos = 0
			ypos = 0

		if 'position="' in line:
			n1 = line.find('position="', 0)
			n2 = line.find('"', n1)
			n3 = line.find(',', n2)
			n4 = line.find('"', n3)
			x = line[(n2 + 1):n3]
			y = line[(n3 + 1):n4]
			if "c+" in x:
				x1 = x.replace("c+", "")
				x1new = str(int(round_half_up(float(int(x1) * FACT + xpos), r_par)))
				xnew = "c+" + x1new
			elif "c-" in x:
				x1 = x.replace("c-", "")
				x1new = str(int(round_half_up(float(int(x1) * FACT + xpos), r_par)))
				xnew = "c-" + x1new
			elif "e-" in x:
				x1 = x.replace("e-", "")
				x1new = str(int(round_half_up(float(int(x1) * FACT + xpos), r_par)))
				xnew = "e-" + x1new
			elif 'ente' in x:
				xnew = 'center'
			else:
				xnew = str(int(round_half_up(float(int(x) * FACT + xpos), r_par)))

			if "c+" in y:
				y1 = y.replace("c+", "")
				y1new = str(int(round_half_up(float(int(y1) * FACT + ypos), r_par)))
				ynew = "c+" + y1new
			elif "c-" in y:
				y1 = y.replace("c-", "")
				y1new = str(int(round_half_up(float(int(y1) * FACT + ypos), r_par)))
				ynew = "c-" + y1new
			elif "e-" in y:
				y1 = y.replace("e-", "")
				y1new = str(int(round_half_up(float(int(y1) * FACT + ypos), r_par)))
				ynew = "e-" + y1new
			elif 'ente' in y:
				ynew = 'center'
			else:
				ynew = str(int(round_half_up(float(int(y) * FACT + ypos), r_par)))

			strnew = 'position="' + xnew + ',' + ynew + '"'
			line = line[:n1] + strnew + line[(n4 + 1):]
#font="Regular;20"
		if 'font="' in line and 'alias name="' not in line:
			n1 = line.find('font="', 0)
			n2 = line.find(';', n1)
			n3 = line.find('"', n2)
			y = line[(n2 + 1):n3]
			ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:(n2 + 1)] + ynew + '"'
			line = line[:n1] + strnew + line[(n3 + 1):]
#Font="Regular;20"
		if 'Font="' in line and ' Cool' not in line:
			s = 0
			n3 = 0
			for s in range(0, line.count('Font="')):
				n1 = line.find('Font="', n3)
				n2 = line.find(';', n1)
				n3 = line.find('"', n2)
				y = line[(n2 + 1):n3]
				ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew
				line = line[:n1] + strnew + line[n3:]
#ServiceFontGraphical="epg_text;20" EntryFontGraphical="epg_text;20"
		if 'FontGraphical="' in line and ' Cool' not in line:
			s = 0
			n3 = 0
			for s in range(0, line.count('FontGraphical="')):
				n1 = line.find('FontGraphical="', n3)
				n2 = line.find(';', n1)
				n3 = line.find('"', n2)
				y = line[(n2 + 1):n3]
				ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew
				line = line[:n1] + strnew + line[n3:]
#ServiceFontInfobar="epg_text;20" EntryFontInfobar="epg_text;20"
		if 'FontInfobar=' in line and ' Cool' not in line:
			s = 0
			n3 = 0
			for s in range(0, line.count('FontInfobar="')):
				n1 = line.find('FontInfobar="', n3)
				n2 = line.find(';', n1)
				n3 = line.find('"', n2)
				y = line[(n2 + 1):n3]
				ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew
				line = line[:n1] + strnew + line[n3:]
#EventFontSingle="epg_event;22"
		if 'FontSingle=' in line and ' Cool' not in line:
			s = 0
			n3 = 0
			for s in range(0, line.count('FontSingle="')):
				n1 = line.find('FontSingle="', n3)
				n2 = line.find(';', n1)
				n3 = line.find('"', n2)
				y = line[(n2 + 1):n3]
				ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew
				line = line[:n1] + strnew + line[n3:]
#EventFontMulti="epg_event;22"
		if 'FontMulti=' in line and ' Cool' not in line:
			s = 0
			n3 = 0
			for s in range(0, line.count('FontMulti="')):
				n1 = line.find('FontMulti="', n3)
				n2 = line.find(';', n1)
				n3 = line.find('"', n2)
				y = line[(n2 + 1):n3]
				ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew
				line = line[:n1] + strnew + line[n3:]
#TimeFontVertical="epg_event;22" EventFontVertical="epg_event;18"
		if 'FontVertical=' in line and ' Cool' not in line:
			s = 0
			n3 = 0
			for s in range(0, line.count('FontVertical="')):
				n1 = line.find('FontVertical="', n3)
				n2 = line.find(';', n1)
				n3 = line.find('"', n2)
				y = line[(n2 + 1):n3]
				ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew
				line = line[:n1] + strnew + line[n3:]
#<alias name="Body" font="screen_text" size="20" height="25" />
		if 'font="' in line and 'alias name="' in line and 'size="' in line:
			n1 = line.find('size="', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', n2 + 1)
			y = line[(n2 + 1):n3]
			ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:(n2 + 1)] + ynew + '"'
			line = line[:n1] + strnew + line[(n3 + 1):]
#<alias name="Body" font="screen_text" size="20" height="25" />
		if 'font="' in line and 'alias name="' in line and 'height="' in line:
			n1 = line.find('height="', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', n2 + 1)
			y = line[(n2 + 1):n3]
			ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:(n2 + 1)] + ynew + '"'
			line = line[:n1] + strnew + line[(n3 + 1):]
#"fonts": [gFont("Regular",18),gFont("Regular",14),gFont("Regular",24),gFont("Regular",20)]
		if '"fonts":' in line and 'gFont' in line:
			s = 0
			n3 = 0
			for s in range(0, line.count('gFont(')):
				n1 = line.find('gFont(', n3)
				n2 = line.find(',', n1)
				n3 = line.find(')', n2)
				y = line[(n2 + 1):n3]
				ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + " " + ynew
				line = line[:n1] + strnew + line[n3:]
#(pos = (40, 5)
		if '(pos' in line and ')' in line:
			n1 = line.find('(pos', 0)
			n2 = line.find('(', n1 + 1)
			n3 = line.find(',', n2)
			n4 = line.find(')', n3)
			x = line[(n2 + 1):n3]
			y = line[(n3 + 1):n4]
			if "c+" in x:
				x1 = x.replace("c+", "")
				x1new = str(int(round_half_up(float(int(x1) * FACT), r_par)))
				xnew = "c+" + x1new
			elif "c-" in x:
				x1 = x.replace("c-", "")
				x1new = str(int(round_half_up(float(int(x1) * FACT), r_par)))
				xnew = "c-" + x1new
			elif "e-" in x:
				x1 = x.replace("e-", "")
				x1new = str(int(round_half_up(float(int(x1) * FACT), r_par)))
				xnew = "e-" + x1new
			elif 'ente' in x:
				xnew = 'center'
			else:
				xnew = str(int(round_half_up(float(int(x) * FACT), r_par)))

			if "c+" in y:
				y1 = y.replace("c+", "")
				y1new = str(int(round_half_up(float(int(y1) * FACT), r_par)))
				ynew = "c+" + y1new
			elif "c-" in y:
				y1 = y.replace("c-", "")
				y1new = str(int(round_half_up(float(int(y1) * FACT), r_par)))
				ynew = "c-" + y1new
			elif "e-" in y:
				y1 = y.replace("e-", "")
				y1new = str(int(round_half_up(float(int(y1) * FACT), r_par)))
				ynew = "e-" + y1new
			elif 'ente' in y:
				ynew = 'center'
			else:
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))

			strnew = '(pos = (' + xnew + ', ' + ynew + ')'
			line = line[:n1] + strnew + line[(n4 + 1):]
#size = (500, 45)
			if 'size' in line and '(' in line and ')' in line:
				n1 = line.find('size', 0)
				n2 = line.find('(', n1)
				n3 = line.find(',', n2)
				n4 = line.find(')', n3)
				x = line[(n2 + 1):n3]
				y = line[(n3 + 1):n4]
				if "c+" in x:
					x1 = x.replace("c+", "")
					x1new = str(int(round_half_up(float(int(x1) * FACT), r_par)))
					xnew = "c+" + x1new
				elif "c-" in x:
					x1 = x.replace("c-", "")
					x1new = str(int(round_half_up(float(int(x1) * FACT), r_par)))
					xnew = "c-" + x1new
				elif "e-" in x:
					x1 = x.replace("e-", "")
					x1new = str(int(round_half_up(float(int(x1) * FACT), r_par)))
					xnew = "e-" + x1new
				elif 'ente' in x:
					xnew = 'center'
				else:
					xnew = str(int(round_half_up(float(int(x) * FACT), r_par)))

				if "c+" in y:
					y1 = y.replace("c+", "")
					y1new = str(int(round_half_up(float(int(y1) * FACT), r_par)))
					ynew = "c+" + y1new
				elif "c-" in y:
					y1 = y.replace("c-", "")
					y1new = str(int(round_half_up(float(int(y1) * FACT), r_par)))
					ynew = "c-" + y1new
				elif "e-" in y:
					y1 = y.replace("e-", "")
					y1new = str(int(round_half_up(float(int(y1) * FACT), r_par)))
					ynew = "e-" + y1new
				elif 'ente' in y:
					ynew = 'center'
				else:
					ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))

				strnew = 'size = (' + xnew + ', ' + ynew + ')'
				line = line[:n1] + strnew + line[(n4 + 1):]
#offset="5,0"
		if ' offset="' in line:
			n1 = line.find(' offset', 0)
			n2 = line.find('"', n1)
			n3 = line.find(',', n2)
			n4 = line.find('"', n3)
			x = line[(n2 + 1):n3]
			y = line[(n3 + 1):n4]
			xnew = str(int(round_half_up(float(int(x) * FACT), r_par)))
			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))

			strnew = ' offset="' + xnew + ',' + ynew + '"'
			line = line[:n1] + strnew + line[(n4 + 1):]

#itemSpacing="10,10"
		if ' itemSpacing="' in line:
			n1 = line.find(' itemSpacing', 0)
			n2 = line.find('"', n1)
			n3 = line.find(',', n2)
			n4 = line.find('"', n3)
			x = line[(n2 + 1):n3]
			y = line[(n3 + 1):n4]
			xnew = str(int(round_half_up(float(int(x) * FACT), r_par)))
			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))

			strnew = ' itemSpacing="' + xnew + ',' + ynew + '"'
			line = line[:n1] + strnew + line[(n4 + 1):]


#fieldMargins="10"
		if 'fieldMargins="' in line:
			n1 = line.find('fieldMargins="', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', n2 + 1)
			y = line[(n2 + 1):n3]

			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + ynew + '"'
			line = line[:n1] + strnew + line[(n3 + 1):]
#itemsDistances="10"
		if 'itemsDistances="' in line:
			n1 = line.find('itemsDistances="', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', n2 + 1)
			y = line[(n2 + 1):n3]

			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + ynew + '"'
			line = line[:n1] + strnew + line[(n3 + 1):]
#progressbarHeight="10"
		if 'progressbarHeight="' in line:
			n1 = line.find('progressbarHeight="', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', n2 + 1)
			y = line[(n2 + 1):n3]

			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + ynew + '"'
			line = line[:n1] + strnew + line[(n3 + 1):]
#progressBarWidth="50"
		if 'progressBarWidth="' in line:
			n1 = line.find('progressBarWidth="', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', n2 + 1)
			y = line[(n2 + 1):n3]

			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + ynew + '"'
			line = line[:n1] + strnew + line[(n3 + 1):]
#progressbarBorderWidth="1" -> deactivated (channel list)
		#if 'progressbarBorderWidth="' in line:
		#	n1 = line.find('progressbarBorderWidth="', 0)
		#	n2 = line.find('"', n1)
		#	n3 = line.find('"', n2+1)
		#	y = line[(n2+1):n3]

		#	ynew = str(int(round_half_up(float(int(y)*FACT),r_par)))
		#	strnew = line[n1:n2+1] + ynew + '"'
		#	line = line[:n1] + strnew + line[(n3+1):]
#itemHeight="25"
		if 'itemHeight="' in line:
			# print('################################################ 1')
			n1 = line.find('itemHeight="', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', n2 + 1)
			y = line[(n2 + 1):n3]

			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + ynew + '"'
			line = line[:n1] + strnew + line[(n3 + 1):]
#"itemHeight": 45
		if '"itemHeight":' in line:
			n1 = line.find('"itemHeight":', 0)
			n2 = line.find(':', n1)
			n3 = line.find(',', n2)
			if n3 == -1:
				n3 = line.find(')', n2)
				if n3 == -1:
					n3 = line.find('}', n2)
			y = line[(n2 + 1):n3]

			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + " " + ynew
			line = line[:n1] + strnew + line[n3:]

#itemWidth="25"
		if 'itemWidth="' in line:
			# print('################################################ 1')
			n1 = line.find('itemWidth="', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', n2 + 1)
			y = line[(n2 + 1):n3]

			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + ynew + '"'
			line = line[:n1] + strnew + line[(n3 + 1):]
#"itemWidth": 45
		if '"itemWidth":' in line:
			n1 = line.find('"itemWidth":', 0)
			n2 = line.find(':', n1)
			n3 = line.find(',', n2)
			if n3 == -1:
				n3 = line.find(')', n2)
				if n3 == -1:
					n3 = line.find('}', n2)
			y = line[(n2 + 1):n3]

			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + " " + ynew
			line = line[:n1] + strnew + line[n3:]

#": (90,[
		if '": (' in line and '[' in line:
			n1 = line.find('":', 0)
			n2 = line.find('(', n1)
			n3 = line.find(',', n2 + 1)
			y = line[(n2 + 1):n3]

			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + ynew
			line = line[:n1] + strnew + line[n3:]

#messagebox <applet type="onLayoutFinish">
#offset_listposx = 10
#offset_listposy = 10
#offset_listwidth = 10
#offset_listheight = 30
#offset_textwidth = 20
#offset_textheight = 90
#min_width = 400
#min_height = 50
#offset = 21
		if 'offset_listposx =' in line:
			n1 = line.find('offset_listposx', 0)
			n2 = line.find('=', n1)
			n3 = line.find(',', n2)
			if n3 == -1:
				n3 = line.find(')', n2)
				if n3 == -1:
					n3 = line.find('}', n2)
			x = line[(n2 + 1):n3]
			xnew = str(int(round_half_up(float(int(x) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + " " + xnew
			line = line[:n1] + strnew + line[n3:]
		elif 'offset_listposy =' in line:
			n1 = line.find('offset_listposy', 0)
			n2 = line.find('=', n1)
			n3 = line.find(',', n2)
			if n3 == -1:
				n3 = line.find(')', n2)
				if n3 == -1:
					n3 = line.find('}', n2)
			y = line[(n2 + 1):n3]
			xnew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + " " + xnew
			line = line[:n1] + strnew + line[n3:]
		elif 'offset_listwidth =' in line:
			n1 = line.find('offset_listwidth', 0)
			n2 = line.find('=', n1)
			n3 = line.find(',', n2)
			if n3 == -1:
				n3 = line.find(')', n2)
				if n3 == -1:
					n3 = line.find('}', n2)
			x = line[(n2 + 1):n3]
			xnew = str(int(round_half_up(float(int(x) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + " " + xnew
			line = line[:n1] + strnew + line[n3:]
		elif 'offset_listheight =' in line:
			n1 = line.find('offset_listheight', 0)
			n2 = line.find('=', n1)
			n3 = line.find(',', n2)
			if n3 == -1:
				n3 = line.find(')', n2)
				if n3 == -1:
					n3 = line.find('}', n2)
			y = line[(n2 + 1):n3]
			xnew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + " " + xnew
			line = line[:n1] + strnew + line[n3:]
		elif 'offset_textwidth =' in line:
			n1 = line.find('offset_textwidth', 0)
			n2 = line.find('=', n1)
			n3 = line.find(',', n2)
			if n3 == -1:
				n3 = line.find(')', n2)
				if n3 == -1:
					n3 = line.find('}', n2)
			x = line[(n2 + 1):n3]
			xnew = str(int(round_half_up(float(int(x) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + " " + xnew
			line = line[:n1] + strnew + line[n3:]
		elif 'offset_textheight =' in line:
			n1 = line.find('offset_textheight', 0)
			n2 = line.find('=', n1)
			n3 = line.find(',', n2)
			if n3 == -1:
				n3 = line.find(')', n2)
				if n3 == -1:
					n3 = line.find('}', n2)
			y = line[(n2 + 1):n3]
			xnew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + " " + xnew
			line = line[:n1] + strnew + line[n3:]
		elif 'min_width =' in line:
			n1 = line.find('min_width', 0)
			n2 = line.find('=', n1)
			n3 = line.find(',', n2)
			if n3 == -1:
				n3 = line.find(')', n2)
				if n3 == -1:
					n3 = line.find('}', n2)
			x = line[(n2 + 1):n3]
			xnew = str(int(round_half_up(float(int(x) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + " " + xnew
			line = line[:n1] + strnew + line[n3:]
		elif 'min_height =' in line:
			n1 = line.find('min_height', 0)
			n2 = line.find('=', n1)
			n3 = line.find(',', n2)
			if n3 == -1:
				n3 = line.find(')', n2)
				if n3 == -1:
					n3 = line.find('}', n2)
			y = line[(n2 + 1):n3]
			xnew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + " " + xnew
			line = line[:n1] + strnew + line[n3:]
		elif 'offset =' in line:
			n1 = line.find('offset', 0)
			n2 = line.find('=', n1)
			n3 = line.find(',', n2)
			if n3 == -1:
				n3 = line.find(')', n2)
				if n3 == -1:
					n3 = line.find('}', n2)
			y = line[(n2 + 1):n3]
			xnew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + " " + xnew
			line = line[:n1] + strnew + line[n3:]
#emc special start
		if 'widget name="list"' in line and ' Cool' in line and ' CoolEvent' not in line or 'render="PositionGauge"' in line:
#CoolFont="epg_text;20" CoolSelectFont="epg_text;20" CoolDateFont="epg_text;30"
			if 'CoolFont="' in line:
				n1 = line.find('CoolFont=', 0)
				n2 = line.find(';', n1)
				n3 = line.find('"', n2)
				y = line[(n2 + 1):n3]
				ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
			if 'CoolSelectFont="' in line:
				n1 = line.find('CoolSelectFont=', 0)
				n2 = line.find(';', n1)
				n3 = line.find('"', n2)
				y = line[(n2 + 1):n3]
				ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
			if 'CoolDateFont=' in line:
				n1 = line.find('CoolDateFont=', 0)
				n2 = line.find(';', n1)
				n3 = line.find('"', n2)
				y = line[(n2 + 1):n3]
				ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolSelNumTxtWidth="26"
			if 'CoolSelNumTxtWidth="' in line:
				n1 = line.find('CoolSelNumTxtWidth=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolDateHPos="1"
			if 'CoolDateHPos="' in line:
				n1 = line.find('CoolDateHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolProgressHPos="1"
			if 'CoolProgressHPos="' in line:
				n1 = line.find('CoolProgressHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolMovieHPos="1"
			if 'CoolMovieHPos="' in line:
				n1 = line.find('CoolMovieHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolDirInfoWidth="110"
			if 'CoolDirInfoWidth="' in line:
				n1 = line.find('CoolDirInfoWidth=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolCSWidth="110"
			if 'CoolCSWidth="' in line:
				n1 = line.find('CoolCSWidth=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolProgressPos="35"
			if 'CoolProgressPos="' in line:
				n1 = line.find('CoolProgressPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolIconPos="35"
			if 'CoolIconPos="' in line:
				n1 = line.find('CoolIconPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolIconHPos="35"
			if 'CoolIconHPos="' in line:
				n1 = line.find('CoolIconHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolBarPos="35"
			if 'CoolBarPos="' in line:
				n1 = line.find('CoolBarPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolBarHPos="10"
			if 'CoolBarHPos="' in line:
				n1 = line.find('CoolBarHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolMoviePos="110"
			if 'CoolMoviePos="' in line:
				n1 = line.find('CoolMoviePos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolDatePos="590"
			if 'CoolDatePos="' in line:
				n1 = line.find('CoolDatePos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolCSPos"590"
			if 'CoolCSPos="' in line:
				n1 = line.find('CoolCSPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolMovieSize="490"
			if 'CoolMovieSize="' in line:
				n1 = line.find('CoolMovieSize=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolFolderSize="490"
			if 'CoolFolderSize="' in line:
				n1 = line.find('CoolFolderSize="', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolDateWidth="110"
			if 'CoolDateWidth="' in line:
				n1 = line.find('CoolDateWidth=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolPiconPos="100"
			if 'CoolPiconPos="' in line:
				n1 = line.find('CoolPiconPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolPiconHPos="2"
			if 'CoolPiconHPos="' in line:
				n1 = line.find('CoolPiconHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolPiconWidth="60"
			if 'CoolPiconWidth="' in line:
				n1 = line.find('CoolPiconWidth=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolPiconHeight="26"
			if 'CoolPiconHeight="' in line:
				n1 = line.find('CoolPiconHeight=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolMoviePiconPos="160"
			if 'CoolMoviePiconPos="' in line:
				n1 = line.find('CoolMoviePiconPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolMoviePiconSize="425"
			if 'CoolMoviePiconSize="' in line:
				n1 = line.find('CoolMoviePiconSize=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolIconSize="24,24"
			if 'CoolIconSize="' in line:
				n1 = line.find('CoolIconSize=', 0)
				n2 = line.find('"', n1)
				n3 = line.find(',', n2 + 1)
				n4 = line.find('"', n3)
				x = line[(n2 + 1):n3]
				y = line[(n3 + 1):n4]
				xnew = str(int(round_half_up(float(int(x) * FACT), r_par)))
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = 'CoolIconSize="' + xnew + ',' + ynew + '"'
				line = line[:n1] + strnew + line[(n4 + 1):]
#CoolBarSize="65,10"
			if 'CoolBarSize="' in line:
				n1 = line.find('CoolBarSize=', 0)
				n2 = line.find('"', n1)
				n3 = line.find(',', n2 + 1)
				n4 = line.find('"', n3)
				x = line[(n2 + 1):n3]
				y = line[(n3 + 1):n4]
				xnew = str(int(round_half_up(float(int(x) * FACT), r_par)))
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = 'CoolBarSize="' + xnew + ',' + ynew + '"'
				line = line[:n1] + strnew + line[(n4 + 1):]
#CoolBarSizeSa="65,10"
			if 'CoolBarSizeSa="' in line:
				n1 = line.find('CoolBarSizeSa=', 0)
				n2 = line.find('"', n1)
				n3 = line.find(',', n2 + 1)
				n4 = line.find('"', n3)
				x = line[(n2 + 1):n3]
				y = line[(n3 + 1):n4]
				xnew = str(int(round_half_up(float(int(x) * FACT), r_par)))
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = 'CoolBarSizeSa="' + xnew + ',' + ynew + '"'
				line = line[:n1] + strnew + line[(n4 + 1):]
#/CoolPointerRec.png:980,0"
			if '/CoolPointerRec.png:' in line:
				n1 = line.find('/CoolPointerRec.png', 0)
				n2 = line.find(':', n1)
				n3 = line.find(',', n2 + 1)
				n4 = line.find('"', n3)
				x = line[(n2 + 1):n3]
				y = line[(n3 + 1):n4]
				xnew = str(int(round_half_up(float(int(x) * FACT), r_par)))
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = '/CoolPointerRec.png:' + xnew + ',' + ynew + '"'
				line = line[:n1] + strnew + line[(n4 + 1):]
#/CoolPointerRec2.png:1080,0"
			if '/CoolPointerRec2.png:' in line:
				n1 = line.find('/CoolPointerRec2.png', 0)
				n2 = line.find(':', n1)
				n3 = line.find(',', n2 + 1)
				n4 = line.find('"', n3)
				x = line[(n2 + 1):n3]
				y = line[(n3 + 1):n4]
				xnew = str(int(round_half_up(float(int(x) * FACT), r_par)))
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = '/CoolPointerRec2.png:' + xnew + ',' + ynew + '"'
				line = line[:n1] + strnew + line[(n4 + 1):]

#emc special end
#cool tv guide special start
		if ('widget name="list"' in line or 'widget name="CoolEvent"' in line) and ' CoolEvent' in line:
#CoolFont="Regular;19" CoolServiceFont="Regular;19" CoolEventFont="Regular;19"
			if 'CoolFont="' in line:
				n1 = line.find('CoolFont=', 0)
				n2 = line.find(';', n1)
				n3 = line.find('"', n2)
				y = line[(n2 + 1):n3]
				ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
			if 'CoolServiceFont="' in line:
				n1 = line.find('CoolServiceFont=', 0)
				n2 = line.find(';', n1)
				n3 = line.find('"', n2)
				y = line[(n2 + 1):n3]
				ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
			if 'CoolEventFont="' in line:
				n1 = line.find('CoolEventFont=', 0)
				n2 = line.find(';', n1)
				n3 = line.find('"', n2)
				y = line[(n2 + 1):n3]
				ynew = str(int(f_offset + round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolServiceSize="220"
			if 'CoolServiceSize="' in line:
				n1 = line.find('CoolServiceSize=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolEventSize="720"
			if 'CoolEventSize="' in line:
				n1 = line.find('CoolEventSize=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolServicePos="4"
			if 'CoolServicePos="' in line:
				n1 = line.find('CoolServicePos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolServiceHPos="1"
			if 'CoolServiceHPos="' in line:
				n1 = line.find('CoolServiceHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolEventPos="355"
			if 'CoolEventPos="' in line:
				n1 = line.find('CoolEventPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolEventHPos="1"
			if 'CoolEventHPos="' in line:
				n1 = line.find('CoolEventHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolBarPos="240"
			if 'CoolBarPos="' in line:
				n1 = line.find('CoolBarPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolBarHPos="10"
			if 'CoolBarHPos="' in line:
				n1 = line.find('CoolBarHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolBarSize="100"
			if 'CoolBarSize="' in line:
				n1 = line.find('CoolBarSize=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolBarHigh="10"
			if 'CoolBarHigh="' in line:
				n1 = line.find('CoolBarHigh=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolTimePos="225"
			if 'CoolTimePos="' in line:
				n1 = line.find('CoolTimePos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolTimeHPos="2"
			if 'CoolTimeHPos="' in line:
				n1 = line.find('CoolTimeHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolTimeSize="120"
			if 'CoolTimeSize="' in line:
				n1 = line.find('CoolTimeSize=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolDurationPos="1055"
			if 'CoolDurationPos="' in line:
				n1 = line.find('CoolDurationPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolDurationSize="100"
			if 'CoolDurationSize="' in line:
				n1 = line.find('CoolDurationSize=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolPico="35"
			if 'CoolPico="' in line:
				n1 = line.find('CoolPico=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolDaySize="100"
			if 'CoolDaySize="' in line:
				n1 = line.find('CoolDaySize=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolDayPos="0"
			if 'CoolDayPos="' in line:
				n1 = line.find('CoolDayPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolDayHPos="2"
			if 'CoolDayHPos="' in line:
				n1 = line.find('CoolDayHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolDayHPos="2"
			if 'CoolDayHPos="' in line:
				n1 = line.find('CoolDayHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolDatePos="0"
			if 'CoolDatePos="' in line:
				n1 = line.find('CoolDatePos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolDateHPos="0"
			if 'CoolDateHPos="' in line:
				n1 = line.find('CoolDateHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolDateSize="0"
			if 'CoolDateSize="' in line:
				n1 = line.find('CoolDateSize=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolMarkerHPos="200"
			if 'CoolMarkerHPos="' in line:
				n1 = line.find('CoolMarkerHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolMarkerPicPos="2"
			if 'CoolMarkerPicPos="' in line:
				n1 = line.find('CoolMarkerPicPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolMarkerPicHPos="2"
			if 'CoolMarkerPicHPos="' in line:
				n1 = line.find('CoolMarkerPicHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolPicoPos="2"
			if 'CoolPicoPos="' in line:
				n1 = line.find('CoolPicoPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#CoolPicoHPos="2"
			if 'CoolPicoHPos="' in line:
				n1 = line.find('CoolPicoHPos=', 0)
				n2 = line.find('"', n1)
				n3 = line.find('"', n2 + 1)
				y = line[(n2 + 1):n3]
				ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
				strnew = line[n1:n2 + 1] + ynew + '"'
				line = line[:n1] + strnew + line[(n3 + 1):]
#cool tv guide special end

#colPosition="240"
		if 'colPosition="' in line:
			n1 = line.find('colPosition=', 0)
			n2 = line.find('"', n1)
			n3 = line.find('"', n2 + 1)
			y = line[(n2 + 1):n3]
			ynew = str(int(round_half_up(float(int(y) * FACT), r_par)))
			strnew = line[n1:n2 + 1] + ynew + '"'
			line = line[:n1] + strnew + line[(n3 + 1):]

		return line

	@staticmethod
	def getTunerCount():
		tunerCount = nimmanager.getSlotCount()
		tunerCount = max(1, tunerCount)
		tunerCount = min(8, tunerCount)
		return tunerCount

	@staticmethod
	def getChannelNameXML(widgetPosition, fontSizeType, showChannelNumber, showChannelName):
		fontSize = "80"

		if fontSizeType == "INFOBARCHANNELNAME-2":
			fontSize = "70"
		elif fontSizeType == "INFOBARCHANNELNAME-3":
			fontSize = "60"
		elif fontSizeType == "INFOBARCHANNELNAME-4":
			fontSize = "50"
		elif fontSizeType == "INFOBARCHANNELNAME-5":
			fontSize = "40"

		if showChannelNumber and showChannelName:
			channelRenderer = "ServiceNumberAndName"
		elif showChannelNumber:
			channelRenderer = "ServiceNumber"
		elif showChannelName:
			channelRenderer = "ServiceName"
		else:
			channelRenderer = None

		if channelRenderer is not None:
			return '''<widget font="global_large;''' + fontSize + '''" backgroundColor="text-background" foregroundColor="background-text" noWrap="1" position="''' \
				+ widgetPosition \
				+ '''" render="Label" size="1252,105" source="session.CurrentService" transparent="1" valign="bottom" zPosition="-30">
				<convert type="MetrixHDExtServiceInfo">''' + channelRenderer + '''</convert>
			</widget>'''

		return ""


# applySkinSettings taken from OverlayHD
def applySkinSettings(fullInit=False):
	ActivateSkinSettings().initConfigs()
	colorelements = [
		("layer-a-channelselection-foreground", "channelselectionservice", ""),
		("layer-a-channelselection-foregroundColorSelected", "channelselectionserviceselected", ""),
		("layer-a-channelselection-foreground-ServiceDescription", "channelselectionservicedescription", ""),
		("layer-a-channelselection-progressbar", "channelselectionprogress", ""),
		("layer-a-channelselection-progressbarborder", "channelselectionprogressborder", ""),
		("layer-a-channelselection-foreground-ServiceDescriptionSelected", "channelselectionservicedescriptionselected", ""),
		("layer-a-channelselection-foreground-colorServiceRecorded", "channelselectioncolorServiceRecorded", ""),
		("layer-a-channelselection-foreground-colorServicePseudoRecorded", "channelselectioncolorServicePseudoRecorded", ""),
		("layer-a-channelselection-foreground-colorServiceStreamed", "channelselectioncolorServiceStreamed", ""),

		("title-foreground", "windowtitletext", "windowtitletexttransparency"),
		("title-background", "windowtitletextback", "windowtitletextbacktransparency"),
		("background-text", "backgroundtext", "backgroundtexttransparency"),
		("text-background", "backgroundtextback", "backgroundtextbacktransparency"),

		("layer-a-title-foreground", "windowtitletext", ""),
		("layer-a-button-foreground", "buttonforeground", ""),

		("scrollbarSlidercolor", "scrollbarSlidercolor", "scrollbarSlidertransparency"),
		("scrollbarSliderbordercolor", "scrollbarSliderbordercolor", "scrollbarSliderbordertransparency"),

	]

	for colorelement in ["menufont", "menufontselected", "infobarfont1", "infobarfont2", "infobaraccent1", "infobaraccent2", "layer-a-clock-foreground", "layer-b-clock-foreground", "epg-timeline-foreground", "epg-service-now-foreground", "epg-service-foreground", "epg-event-selected-foreground", "epg-event-now-foreground", "epg-primetime-foreground", "epg-event-foreground", "epg-eventdescription-foreground", "layer-b-accent1", "layer-b-accent2", "layer-b-selection-foreground", "layer-b-foreground", "layer-a-extendedinfo1", "layer-a-extendedinfo2", "layer-a-accent1", "layer-a-accent2", "layer-a-selection-foreground", "layer-a-foreground"]:
		colorelements.append((colorelement, colorelement.replace("-", ""), ""))

	for colorelement in ["menubackground", "menusymbolbackground", "infobarbackground", "infobarprogress", "weather-borderlines", "epg-timeline-background", "epg-service-now-background", "epg-service-background", "epg-event-selected-background", "epg-event-now-background", "epg-primetime-background", "epg-event-background", "epg-background", "epg-borderlines", "epg-eventdescription-background", "layer-b-progress", "layer-b-selection-background", "layer-b-background", "layer-a-underline", "layer-a-progress", "layer-a-selection-background", "layer-a-background"]:
		colorelements.append((colorelement, colorelement.replace("-", ""), f"{colorelement.replace('-', '')}transparency"))

	for (label, color, transparency) in colorelements:

		if color and transparency:
			colorobject = getattr(config.plugins.MyMetrixLiteColors, color)
			transobject = getattr(config.plugins.MyMetrixLiteColors, transparency)
			colorvalue = f"#{transobject.value}{colorobject.value}"
		elif color:
			colorobject = getattr(config.plugins.MyMetrixLiteColors, color)
			colorvalue = f"#00{colorobject.value}"
		else:
			continue

		colors[label] = parseColor(colorvalue)

	reloadWindowStyles()
