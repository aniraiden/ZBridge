/*
	Copyright (c)2011 - Pixologic Inc. All rights reserved.

  All title and intellectual property rights in and to the SDK and any copies of the SDK,
  are owned by Licensor.
  All title and intellectual property rights in and to the content which may be accessed
  through use of the SDK is the property of the respective content owner and may be protected
  by applicable copyright or other intellectual property laws and treaties.
  This Agreement grants you no rights to use such content.

	NO WARRANTIES. Licensor expressly disclaims any warranty for the SDK.
  THE SDK AND ANY RELATED DOCUMENTATION IS PROVIDED «AS IS» WITHOUT WARRANTY OF ANY KIND,
  EITHER EXPRESS OR IMPLIED, INCLUDING, WITHOUT LIMITATION, THE IMPLIED WARRANTIES
  OR MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, OR NONINFRINGEMENT.
  THE ENTIRE RISK ARISING OUT OF USE OR PERFORMANCE OF THE SDK REMAINS WITH YOU.
	
	BY INSTALLING, COPYING, OR USING THE SDK, YOU AGREE TO BE BOUND BY THE TERMS OF THIS AGREEMENT.
  IF YOU DO NOT AGREE TO THE TERMS OF THIS AGREEMENT, DO NOT INSTALL OR USE THE SDK.
*/

#ifndef __GOZ_UTILS_H__
#define __GOZ_UTILS_H__

#include "GoZ_Config.h"
#include "GoZ_Binary.h"
#include <stdio.h>


class GoZ_Utils
{
public:
  // Some functions for GoZ binary file format I/O.
  static FILE* openGoZFile4Read(const char* pFileName);
  static bool readGoZBlocHeader(FILE* pFile, GoZ_Header* pOutHeader);
  static bool skipGoZBloc(FILE* pFile, const GoZ_Header* pHeader);
  static bool readGoZBlocData(FILE* pFile, const GoZ_Header* pHeader, void *pOutData);
  static FILE* openGoZFile4Write(const char* pFileName, const char* pText);
  static bool writeGoZBloc(FILE* pFile, int itemTag, int itemsCount, void *pItems, float modifier=0);
  static void closeGoZFile(FILE* pFile);

  // Some functions for Preference File Format I/O.
  static bool readPref(const char* pFileName, const char* pPrefName, char* pOutPrefValue, int pOutPrefValueSize);
  static bool writePref(const char* pFileName, const char* pPrefName, const char* pPrefValue);
  static bool readStringPref(const char* pFileName, const char* pPrefName, char* pOutPrefValue, int pOutPrefValueSize);
  static bool writeStringPref(const char* pFileName, const char* pPrefName, char* pPrefValue);
  static bool readBoolPref(const char* pFileName, const char* pPrefName, bool* pOutPrefValue);
  static bool writeBoolPref(const char* pFileName, const char* pPrefName, bool prefValue);
  static bool readIntPref(const char* pFileName, const char* pPrefName, int* pOutPrefValue);
  static bool writeIntPref(const char* pFileName, const char* pPrefName, int prefValue);
  static bool readFloatPref(const char* pFileName, const char* pPrefName, float* pOutPrefValue);
  static bool writeFloatPref(const char* pFileName, const char* pPrefName, float prefValue);

  // Some functions for GoZ-enabled applications.
  static bool readGoZAppPath(const char* pGoZAppID, char* pOutPath, int pOutPathSize);
  static bool readZBrushAppPath(char* pOutPath, int pOutPathSize);
  static bool findRunningAppProcessID(char* pAppPath, GoZ_ProcessID* pOutProcessID);


public:
  static const char* s_pixologicSharedFolder;
  static const char* s_folderSeparator;
};

#endif  // __GOZ_UTILS_H__
