/*
  Copyright (c)2010 - Pixologic Inc. All rights reserved.

  THIS MATERIAL IS PROVIDED AS IS, WITH ABSOLUTELY NO WARRANTY
  EXPRESSED OR IMPLIED. ANY USE IS AT YOUR OWN RISK.

  Permission is hereby granted to use or copy this source code ONLY
  in order to exchange data between Pixologic ZBrush and any other
  application, provided the above notices are retained on all copies.

  IT IS ABSOLUTELY FORBIDDEN TO USE THIS SOURCE CODE AND/OR ANY
  STRUCTURE/DATA IT CONTAINS FOR ANY OTHER PURPOSE, AS FOR EXAMPLE
  EXCHANGING DATA BETWEEN 2 OTHER APPLICATIONS.

  Permission to modify the code and to distribute modified code is
  granted, provided the above notices are retained, and a notice that
  the code was modified is included with the above copyright notice.
*/

#include "GoZ_Utils.h"


// OS specific definitions...
#ifdef  GOZ_WIN
#include <psapi.h>
#pragma comment (lib, "psapi.lib")

const char*
GoZ_Utils::s_pixologicSharedFolder = "C:\\Users\\Public\\Pixologic";

const char*
GoZ_Utils::s_folderSeparator = "\\";


#else   // GOZ_MAC
const char*
GoZ_Utils::s_pixologicSharedFolder = "/Users/Shared/Pixologic";

const char*
GoZ_Utils::s_folderSeparator = "/";
#endif  // GOZ_OS

static int strcmp_nocase(const char* str1, const char* str2);
static int strncmp_nocase(const char* str1, const char* str2, int count);


// Some functions for GoZ binary file format I/O.
FILE*
GoZ_Utils::openGoZFile4Read(const char* pFileName)
{
  FILE* pFile = fopen(pFileName, "rb");
  if (pFile != NULL)
  {
    char gozHeader[32];
    if ((fread(gozHeader, 1, 32, pFile)!=32) || strncmp_nocase(gozHeader, "GoZb", 4))
    {
      fclose(pFile);
      pFile = NULL;
    }
  }
  return pFile;
}

bool
GoZ_Utils::readGoZBlocHeader(FILE* pFile, GoZ_Header* pOutHeader)
{
  return (fread(pOutHeader, 1, sizeof(GoZ_Header), pFile) == sizeof(GoZ_Header));
}

bool
GoZ_Utils::skipGoZBloc(FILE* pFile, const GoZ_Header* pHeader)
{
  int blocSize = pHeader->size - sizeof(GoZ_Header);
  return !fseek(pFile, ftell(pFile)+blocSize, SEEK_SET);
}

bool
GoZ_Utils::readGoZBlocData(FILE* pFile, const GoZ_Header* pHeader, void *pOutData)
{
  int blocSize = pHeader->size - sizeof(GoZ_Header);
  int itemsCount = pHeader->iCount;
  int itemTag = pHeader->tag;
  int dataSize = 0;
  switch (itemTag)
  {
  case GoZ_TAG_END_OF_FILE:
  default:
    dataSize = 0;
    break;
  case GoZ_TAG_MESH:
  case GoZ_TAG_MATERIAL:
  case GoZ_TAG_TEXTURE_MAP_PATH:
  case GoZ_TAG_NORMAL_MAP_PATH:
  case GoZ_TAG_DISPLACEMENT_MAP_PATH:
    dataSize = blocSize;
    break;
  case GoZ_TAG_FLAGS:
    dataSize = 4;
    break;
  case GoZ_TAG_POINT_LIST:
    dataSize = 12*itemsCount;
    break;
  case GoZ_TAG_DPOINT_LIST:
    dataSize = 24*itemsCount;
    break;
  case GoZ_TAG_FACE4_LIST_FORMAT_1:
  case GoZ_TAG_FACE4_LIST_FORMAT_2:
    dataSize = 16*itemsCount;
    break;
  case GoZ_TAG_FACE3_LIST:
    dataSize = 12*itemsCount;
    break;
  case GoZ_TAG_UV4_LIST:
    dataSize = 32*itemsCount;
    break;
  case GoZ_TAG_UV3_LIST:
    dataSize = 24*itemsCount;
    break;
  case GoZ_TAG_MASK8_LIST:
    dataSize = itemsCount;
    break;
  case GoZ_TAG_MASK16_LIST:
    dataSize = 2*itemsCount;
    break;
  case GoZ_TAG_MRGB_LIST:
    dataSize = 4*itemsCount;
    break;
  case GoZ_TAG_GROUPS_LIST:
    dataSize = 2*itemsCount;
    break;
  case GoZ_TAG_CREASE_LIST:
	  dataSize = itemsCount;
	  break;    
  }
  if (dataSize && (fread(pOutData, 1, dataSize, pFile)!=dataSize))
    return false;
  if ((blocSize>dataSize) && fseek(pFile, ftell(pFile)+blocSize-dataSize, SEEK_SET))
    return false;
  return true;
}

FILE*
GoZ_Utils::openGoZFile4Write(const char* pFileName, const char* pText)
{
  FILE* pFile = fopen(pFileName, "wb");
  if (pFile != NULL)
  {
    char gozHeader[32];
    memset(gozHeader, 0, sizeof(gozHeader));
    strcpy(gozHeader, "GoZb");
    if (pText)
    {
      strcpy(gozHeader+4, pText);
      gozHeader[31] = 0;
    }
    if (fwrite(gozHeader, 1, 32, pFile)!=32)
    {
      fclose(pFile);
      pFile = NULL;
    }
  }
  return pFile;
}

bool
GoZ_Utils::writeGoZBloc(FILE* pFile, int itemTag, int itemsCount, void *pItems, float modifier)
{
  int headerSize = sizeof(GoZ_Header);
  int dataSize = 0;
  int padSize = 0;
  switch (itemTag)
  {
  case GoZ_TAG_END_OF_FILE:
    headerSize = 0;
    break;
  default:
    break;
  case GoZ_TAG_MESH:
  case GoZ_TAG_MATERIAL:
  case GoZ_TAG_TEXTURE_MAP_PATH:
  case GoZ_TAG_NORMAL_MAP_PATH:
  case GoZ_TAG_DISPLACEMENT_MAP_PATH:
    dataSize = strlen((const char*)pItems)+1;
    padSize = ((dataSize+3)&~3)-dataSize;
    break;
  case GoZ_TAG_FLAGS:
    dataSize = 4;
    break;
  case GoZ_TAG_POINT_LIST:
    dataSize = 12*itemsCount;
    break;
  case GoZ_TAG_DPOINT_LIST:
    dataSize = 24*itemsCount;
    break;
  case GoZ_TAG_FACE4_LIST_FORMAT_1:
  case GoZ_TAG_FACE4_LIST_FORMAT_2:
    dataSize = 16*itemsCount;
    break;
  case GoZ_TAG_FACE3_LIST:
    dataSize = 12*itemsCount;
    break;
  case GoZ_TAG_UV4_LIST:
    dataSize = 32*itemsCount;
    break;
  case GoZ_TAG_UV3_LIST:
    dataSize = 24*itemsCount;
    break;
  case GoZ_TAG_MASK8_LIST:
    dataSize = itemsCount;
    break;
  case GoZ_TAG_MASK16_LIST:
    dataSize = 2*itemsCount;
    break;
  case GoZ_TAG_MRGB_LIST:
    dataSize = 4*itemsCount;
    break;
  case GoZ_TAG_GROUPS_LIST:
    dataSize = 2*itemsCount;
    break;
  case GoZ_TAG_CREASE_LIST:
	dataSize = itemsCount;
	break; 
  }

  GoZ_Header header;
  header.tag = itemTag;
  header.modifier = modifier;
  header.iCount = itemsCount;
  header.size = headerSize + dataSize + padSize;
  if (fwrite(&header, 1, sizeof(GoZ_Header), pFile) != sizeof(GoZ_Header))
    return false;

  if (dataSize && (fwrite(pItems, 1, dataSize, pFile)!=dataSize))
    return false;
  if (padSize && fseek(pFile, ftell(pFile)+padSize, SEEK_SET))
    return false;
  return true;
}

void
GoZ_Utils::closeGoZFile(FILE* pFile)
{
  fclose(pFile);
}

// Some functions for Preference File Format I/O.
bool
GoZ_Utils::readPref(const char* pFileName, const char* pPrefName, char* pOutPrefValue, int pOutPrefValueSize)
{
  FILE* file = fopen(pFileName, "rb");
  if (file == NULL)
    return false;

  fseek(file, 0, SEEK_END);
  int fileSize = ftell(file);
  bool found = false;
  if (fileSize > 0)
  {
    char str[512];
    char* buffer = new char[fileSize];
    const char *startBuffer = buffer;
    const char *endBuffer = buffer + fileSize;
    const char *startL, *nextL, *endL, *midL, *endT;
    fseek(file, 0, SEEK_SET);
    fread(buffer, 1, fileSize, file);
    for (startL=startBuffer; startL<endBuffer; startL=nextL)
    {
      // Parses the line.
      for (endL=startL; (endL<endBuffer)&&(*endL!=10)&&(*endL!=13); ++endL);            // Gets the end of the line.
      for (nextL=endL; (nextL<endBuffer)&&((*nextL==10)||(*nextL==13)); ++nextL);       // Gets the beginning of the next line.
      for (; (startL<nextL)&&((*startL==' ')||(*startL=='\t')); ++startL);              // Skips spaces at the beginning of the line.
      for (--endL; (endL>=startL)&&((*endL==' ')||(*endL=='\t')); --endL);  ++endL;     // Skips spaces at the end of the line.
      for (midL=startL; (midL<endL)&&(*midL!='='); ++midL);                             // Gets the 'middle' position, separating the preference token and value (character '=').
      for (endT=midL-1; (endT>=startL)&&((*endT==' ')||(*endT=='\t')); --endT); ++endT; // Skips spaces at the end of the token.
      if ((endT-startL)>=sizeof(str)) endT=startL+sizeof(str)-1;                        // Truncs the token if needed.
      str[endT-startL]=0; if (endT>startL) strncpy(str, startL, endT-startL);           // Gets the token as a null terminated string.

      // If we found the right preference, then gets its value.
      if (*str && !strcmp_nocase(str, pPrefName))
      {
        // Parses the value.
        for (++midL; (midL<endL)&&((*midL==' ')||(*midL=='\t')); ++midL);                   // Skips spaces at the beginning of the value.
        if (((endL-midL)>=2)&&(midL[0]==34)&&(endL[-1]==34)) ++midL, --endL;                // Removes start/end commas if any.
        if ((endL-midL)>=pOutPrefValueSize) endL=midL+pOutPrefValueSize-1;                  // Truncs the value if needed.
        pOutPrefValue[endL-midL]=0; if (endL>midL) strncpy(pOutPrefValue, midL, endL-midL); // Gets the value as a null terminated string.

        // Preference was found, no need to search for other occurences.
        found = true;
        break;
      }
    }
    delete [] buffer;
  }
  fclose(file);
  return found;
}

bool
GoZ_Utils::writePref(const char* pFileName, const char* pPrefName, const char* pPrefValue)
{
  if (!(pPrefName && strlen(pPrefName)))
    return false;

  FILE* file = fopen(pFileName, "rb");
  if (file == NULL)
    return false;

  fseek(file, 0, SEEK_END);
  int fileSize = ftell(file);
  if (fileSize > 0)
  {
    char str[512];
    char* buffer = new char[fileSize];
    char* bufferOut = buffer;
    const char* bufferIn;
    const char *startBuffer = buffer;
    const char *endBuffer = buffer + fileSize;
    const char *startL, *nextL, *endL, *midL, *endT;
    fseek(file, 0, SEEK_SET);
    fread(buffer, 1, fileSize, file);
    for (startL=startBuffer; startL<endBuffer; startL=nextL)
    {
      bufferIn = startL;

      // Parses the line.
      for (endL=startL; (endL<endBuffer)&&(*endL!=10)&&(*endL!=13); ++endL);            // Gets the end of the line.
      for (nextL=endL; (nextL<endBuffer)&&((*nextL==10)||(*nextL==13)); ++nextL);       // Gets the beginning of the next line.
      for (; (startL<nextL)&&((*startL==' ')||(*startL=='\t')); ++startL);              // Skips spaces at the beginning of the line.
      for (--endL; (endL>=startL)&&((*endL==' ')||(*endL=='\t')); --endL);  ++endL;     // Skips spaces at the end of the line.
      for (midL=startL; (midL<endL)&&(*midL!='='); ++midL);                             // Gets the 'middle' position, separating the preference token and value (character '=').
      for (endT=midL-1; (endT>=startL)&&((*endT==' ')||(*endT=='\t')); --endT); ++endT; // Skips spaces at the end of the token.
      if ((endT-startL)>=sizeof(str)) endT=startL+sizeof(str)-1;                        // Truncs the token if needed.
      str[endT-startL]=0; if (endT>startL) strncpy(str, startL, endT-startL);           // Gets the token as a null terminated string.

      // Keeps only lines which do not contain the preference to replace.
      if (!*str || strcmp_nocase(str, pPrefName))
      {
        if (bufferOut!=bufferIn)
          memmove(bufferOut, bufferIn, nextL-bufferIn);
        bufferOut += (nextL-bufferIn);
      }
    }

    // Closes the file and reopens it in "Overwrite" mode.
    fclose(file);
    file = fopen(pFileName, "wb");
    if (file == NULL)
    {
      delete [] buffer;
      return false;
    }

    // Writes the output buffer.
    fwrite(buffer, 1, bufferOut-buffer, file);
    delete [] buffer;
  }

  else
  {
    // Closes the file and reopens it in "Overwrite" mode.
    fclose(file);
    file = fopen(pFileName, "wb");
    if (file == NULL)
      return false;
  }

  // Writes the new preference at the end of the file, then closes the file.
  fwrite(pPrefName, 1, strlen(pPrefName), file);
  fwrite(" = ", 1, 3, file);
  if (pPrefValue && strlen(pPrefValue)) fwrite(pPrefValue, 1, strlen(pPrefValue), file);
  fwrite("\n", 1, 1, file);
  fclose(file);
  return true;
}

bool
GoZ_Utils::readStringPref(const char* pFileName, const char* pPrefName, char* pOutPrefValue, int pOutPrefValueSize)
{
  // Reads the "uncleaned" pref value.
  char str[256];
  if (!readPref(pFileName, pPrefName, str, sizeof(str)))
    return false;

  // Removes start/end commas if any.
  int start=0, end=strlen(str);
  if ((end>=2) && (str[0]==34) && (str[end-1]==34))
    ++start, --end;

  // Truncs the string if needed.
  if ((end-start) >= pOutPrefValueSize)
    end = start+pOutPrefValueSize-1;

  // Copy the "cleaned" string.
  str[end] = 0;
  strcpy(pOutPrefValue, str+start);
  return true;
}

bool
GoZ_Utils::writeStringPref(const char* pFileName, const char* pPrefName, char* pPrefValue)
{
  char str[256];
  sprintf(str, "\"%s\"", pPrefValue);
  return writePref(pFileName, pPrefName, str);
}

bool
GoZ_Utils::readBoolPref(const char* pFileName, const char* pPrefName, bool* pOutPrefValue)
{
  char str[256];
  if (!readPref(pFileName, pPrefName, str, sizeof(str)))
    return false;

  if (!(strcmp_nocase(str, "true") && strcmp_nocase(str, "yes") && strcmp_nocase(str, "1") && strcmp_nocase(str, "#t")))
  {
    *pOutPrefValue = true;
    return true;
  }

  else if (!(strcmp_nocase(str, "false") && strcmp_nocase(str, "no") && strcmp_nocase(str, "0") && strcmp_nocase(str, "#f")))
  {
    *pOutPrefValue = false;
    return true;
  }

  else
    return false;
}

bool
GoZ_Utils::writeBoolPref(const char* pFileName, const char* pPrefName, bool prefValue)
{
  const char* pStr = prefValue? "TRUE" : "FALSE";
  return writePref(pFileName, pPrefName, pStr);
}

bool
GoZ_Utils::readIntPref(const char* pFileName, const char* pPrefName, int* pOutPrefValue)
{
  char str[256];
  if (!readPref(pFileName, pPrefName, str, sizeof(str)))
    return false;

  sscanf(str, "%d", pOutPrefValue);
  return true;
}

bool
GoZ_Utils::writeIntPref(const char* pFileName, const char* pPrefName, int prefValue)
{
  char str[256];
  sprintf(str, "%d", prefValue);
  return writePref(pFileName, pPrefName, str);
}

bool
GoZ_Utils::readFloatPref(const char* pFileName, const char* pPrefName, float* pOutPrefValue)
{
  char str[256];
  if (!readPref(pFileName, pPrefName, str, sizeof(str)))
    return false;

  sscanf(str, "%f", pOutPrefValue);
  return true;
}

bool
GoZ_Utils::writeFloatPref(const char* pFileName, const char* pPrefName, float prefValue)
{
  char str[256];
  sprintf(str, "%f", prefValue);
  return writePref(pFileName, pPrefName, str);
}



// Some functions for GoZ-enabled applications.
bool
GoZ_Utils::readGoZAppPath(const char* pGoZAppID, char* pOutPath, int pOutPathSize)
{
  char fileName[256] = "";
  strcat(fileName, s_pixologicSharedFolder);
  strcat(fileName, s_folderSeparator);
  strcat(fileName, "GoZApps");
  strcat(fileName, s_folderSeparator);
  strcat(fileName, pGoZAppID);
  strcat(fileName, s_folderSeparator);
  strcat(fileName, "GoZ_Config.txt");
  return readStringPref(fileName, "PATH", pOutPath, pOutPathSize);
}

bool
GoZ_Utils::readZBrushAppPath(char* pOutPath, int pOutPathSize)
{
  char fileName[256] = "";
  strcat(fileName, s_pixologicSharedFolder);
  strcat(fileName, s_folderSeparator);
  strcat(fileName, "GoZBrush");
  strcat(fileName, s_folderSeparator);
  strcat(fileName, "GoZ_Config.txt");
  return readStringPref(fileName, "PATH", pOutPath, pOutPathSize);
}

bool
GoZ_Utils::findRunningAppProcessID(char* pAppPath, GoZ_ProcessID* pOutProcessID)
{
#ifdef  GOZ_WIN
  // Initializes the resulting processID and returns false if the specified application path is invalid, or if we cannot browse the running applications.
  DWORD processIDs[1024], sizeProcessIDs;
  *pOutProcessID = 0;
  if (!pAppPath || !*pAppPath || !EnumProcesses(processIDs, sizeof(processIDs), &sizeProcessIDs))
    return false;

  // Replaces all backslashes by slashes in the full application path.
  unsigned int i, n;
  for (i=0, n=strlen(pAppPath); i<n; ++i) if (pAppPath[i] == '\\')  pAppPath[i] = '/';

  // Loops on every running process, and tests if it matches the same application path.
  char path[MAX_PATH];
  unsigned int ip, np;
  for (ip=0, np=sizeProcessIDs/sizeof(DWORD); ip<np; ++ip)
  {
    HANDLE hProcess = OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, processIDs[ip]);

    // If we cannot query information on a process, then it is probably because debug privilege is disabled.
    static bool s_debugPrivilegesEnabled = false;
    if ((hProcess==NULL) && !s_debugPrivilegesEnabled)
    {
      HANDLE hToken;
      if (OpenProcessToken(GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES, &hToken))
      {
        LUID luidDebug;
        if (LookupPrivilegeValue(NULL, SE_DEBUG_NAME, &luidDebug))
        {
          TOKEN_PRIVILEGES tokenPriv;
          tokenPriv.PrivilegeCount = 1;
          tokenPriv.Privileges[0].Luid = luidDebug;
          tokenPriv.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED;
          AdjustTokenPrivileges(hToken, FALSE, &tokenPriv, sizeof(tokenPriv), NULL, NULL);
          CloseHandle(hToken);
        }
      }
      hProcess = OpenProcess(PROCESS_QUERY_INFORMATION, FALSE, processIDs[ip]);
      s_debugPrivilegesEnabled = true;
    }

    // If we managed to get information on the running process,
    // then tests if it matches the application path we are searching for.
    if (hProcess != NULL)
    {
      path[0] = 0;
      GetProcessImageFileNameA(hProcess, path, sizeof(path));
      CloseHandle(hProcess);
      // Replaces all backslashes by slashes in the running process full path.
      for (i=0, n=strlen(path); i<n; ++i) if (path[i] == '\\')  path[i] = '/';
      // Tests if this is the application we are searching for.
      // Note: in the running process path, we get a "long text identifier" instead of "[DRIVE]:".
      if (!strcmp_nocase(pAppPath+2, path+n+2-strlen(pAppPath)))
      {
        *pOutProcessID = processIDs[ip];
        return true;
      }
    }
  }
  return false;


#else   // GOZ_MAC
  // Initializes the resulting processID and returns false if the specified application path is invalid.
  FSRef appPathRef, runningAppPathRef;
  pOutProcessID->highLongOfPSN = 0;
  pOutProcessID->lowLongOfPSN = kNoProcess;
  if (FSPathMakeRef((const UInt8 *)pAppPath, &appPathRef, NULL) != noErr)
    return false;

  while (true)
  {
    // Gets the next running application, and returns false in case of any error.
    if ((GetNextProcess(pOutProcessID)!=noErr) || ((pOutProcessID->highLongOfPSN==0) && (pOutProcessID->lowLongOfPSN==kNoProcess)))
    {
      pOutProcessID->highLongOfPSN = 0;
      pOutProcessID->lowLongOfPSN = kNoProcess;
      return false;
    }

    // Gets the location of the running application - just continue on next process in case of error.
    if (GetProcessBundleLocation(pOutProcessID, &runningAppPathRef) != noErr)
      continue;

    // If the running application has the same location: we found our application!
    if (FSCompareFSRefs(&appPathRef, &runningAppPathRef) == noErr)
      return true;
  }
  return false;
#endif  // GOZ_OS
}

static int strcmp_nocase(const char* str1, const char* str2)
{
  if (!str1)  return str2? -1 : 0;
  if (!str2)  return 1;
  for (int c1, c2; (c1=tolower(*(unsigned char*)str1)) != 0; ++str1, ++str2)
  {
    c2 = tolower(*(unsigned char*)str2);
    if (c1 == c2) continue;
    return (c1<c2)? -1 : 1;
  }
  return 0;
}

static int strncmp_nocase(const char* str1, const char* str2, int count)
{
  if (!str1)  return str2? -1 : 0;
  if (!str2)  return 1;
  for (int c1, c2; (c1=tolower(*(unsigned char*)str1)) !=0; ++str1, ++str2, --count)
  {
    if (!count)
      return 0;
    c2 = tolower(*(unsigned char*)str2);
    if (c1 == c2) continue;
    return (c1<c2)? -1 : 1;
  }
  return 0;
}

