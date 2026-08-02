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

#include "GoZ_Mesh.h"


GoZ_Mesh::GoZ_Mesh()
: m_name(NULL),
  m_material(NULL),
  m_flags(0),
  m_vertexCount(0), m_vertices(NULL),
  m_faceCount(0), m_faceType(0), m_vertexIndices(NULL),
  m_uvFaceType(0), m_uvs(NULL),
  m_mask(NULL),
  m_crease( NULL ),
  m_mrgb(NULL),
  m_groups(NULL),
  m_diffuseMap(NULL),
  m_normalMap(NULL),
  m_displacementMap(NULL), m_displacementScale(1.0f)
{
}

GoZ_Mesh::~GoZ_Mesh()
{
  clear();
}

void
GoZ_Mesh::clear()
{
  if (m_name) {delete [] m_name; m_name = NULL;}
  if (m_material) {delete [] m_material; m_material = NULL;}
  m_flags = 0;
  m_vertexCount = 0; if (m_vertices) {delete [] m_vertices; m_vertices = NULL;}
  m_faceCount = 0; m_faceType = 0; if (m_vertexIndices) {delete [] m_vertexIndices; m_vertexIndices = NULL;}
  m_uvFaceType = 0; if (m_uvs) {delete [] m_uvs; m_uvs = NULL;}
  if (m_mask) {delete [] m_mask; m_mask = NULL;}
  if (m_mrgb) {delete [] m_mrgb; m_mrgb = NULL;}
  if (m_groups) {delete [] m_groups; m_groups = NULL;}
  if (m_diffuseMap) {delete [] m_diffuseMap; m_diffuseMap = NULL;}
  if (m_normalMap) {delete [] m_normalMap; m_normalMap = NULL;}
  if (m_crease) { delete[] m_crease; m_crease = NULL; }
  m_displacementScale = 1.0f; if (m_displacementMap) {delete [] m_displacementMap; m_displacementMap = NULL;}
}

bool
GoZ_Mesh::readMesh(const char* fileName)
{
  clear();

  FILE *file = GoZ_Utils::openGoZFile4Read(fileName);
  if (!file)
    return false;

  GoZ_Header blocHeader;
  bool noErr=true, cont=true;
  int count;
  while (noErr && cont)
  {
    if ((noErr = GoZ_Utils::readGoZBlocHeader(file, &blocHeader)) != 0)
    {
      switch (blocHeader.tag)
      {
      case GoZ_TAG_END_OF_FILE:
        cont = false;
        break;
      case GoZ_TAG_MESH:
        count = blocHeader.size-sizeof(GoZ_Header);
        if (count) {m_name = new char[count]; noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, m_name);}
        break;
      case GoZ_TAG_MATERIAL:
        count = blocHeader.size-sizeof(GoZ_Header);
        if (count) {m_material = new char[count]; noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, m_material);}
        break;
      case GoZ_TAG_FLAGS:
        noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, &m_flags);
        break;
      case GoZ_TAG_POINT_LIST:
        m_vertexCount = blocHeader.iCount;
        if (m_vertexCount) {m_vertices = new float[3*m_vertexCount]; noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, m_vertices);}
        break;
      case GoZ_TAG_FACE4_LIST_FORMAT_1:
      case GoZ_TAG_FACE4_LIST_FORMAT_2:
        m_faceCount = blocHeader.iCount;
        m_faceType = blocHeader.tag;
        if (m_faceCount) {m_vertexIndices = new int[4*m_faceCount]; noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, m_vertexIndices);}
        break;
      case GoZ_TAG_FACE3_LIST:
        m_faceCount = blocHeader.iCount;
        m_faceType = blocHeader.tag;
        if (m_faceCount) {m_vertexIndices = new int[3*m_faceCount]; noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, m_vertexIndices);}
        break;
      case GoZ_TAG_UV4_LIST:
        count = blocHeader.iCount;
        m_uvFaceType = blocHeader.tag;
        if (count) {m_uvs = new float[8*count]; noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, m_uvs);}
        break;
      case GoZ_TAG_UV3_LIST:
        count = blocHeader.iCount;
        m_uvFaceType = blocHeader.tag;
        if (count) {m_uvs = new float[6*count]; noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, m_uvs);}
        break;
      case GoZ_TAG_MASK16_LIST:
        count = blocHeader.iCount;
        if (count) {m_mask = new unsigned short[count]; noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, m_mask);}
        break;
      case GoZ_TAG_MRGB_LIST:
        count = blocHeader.iCount;
        if (count) {m_mrgb = new unsigned int[count]; noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, m_mrgb);}
        break;
      case GoZ_TAG_GROUPS_LIST:
        count = blocHeader.iCount;
        if (count) {m_groups = new short[count]; noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, m_groups);}
        break;
      case GoZ_TAG_TEXTURE_MAP_PATH:
        count = blocHeader.size-sizeof(GoZ_Header);
        if (count) {m_diffuseMap = new char[count]; noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, m_diffuseMap);}
        break;
      case GoZ_TAG_NORMAL_MAP_PATH:
        count = blocHeader.size-sizeof(GoZ_Header);
        if (count) {m_normalMap = new char[count]; noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, m_normalMap);}
        break;
      case GoZ_TAG_DISPLACEMENT_MAP_PATH:
        m_displacementScale = blocHeader.modifier;
        count = blocHeader.size-sizeof(GoZ_Header);
        if (count) {m_displacementMap = new char[count]; noErr = GoZ_Utils::readGoZBlocData(file, &blocHeader, m_displacementMap);}
        break;	 
	  case GoZ_TAG_CREASE_LIST:
		  count = blocHeader.iCount;		  
		  if (count) { m_crease = new char[count]; noErr = GoZ_Utils::readGoZBlocData( file, &blocHeader, m_crease ); }
		  break;	 
      default:
        noErr = GoZ_Utils::skipGoZBloc(file, &blocHeader);
        break;
      }
    }
  }
  GoZ_Utils::closeGoZFile(file);
  return noErr;
}

bool
GoZ_Mesh::writeMesh(const char* fileName)
{
  FILE* pFile = GoZ_Utils::openGoZFile4Write(fileName, "Exported by GoZ SDK");
  if (!pFile) return false;
  if (m_name && !GoZ_Utils::writeGoZBloc(pFile, GoZ_TAG_MESH, 1, m_name)) return false;
  if (m_material && !GoZ_Utils::writeGoZBloc(pFile, GoZ_TAG_MATERIAL, 1, m_material)) return false;
  if (!GoZ_Utils::writeGoZBloc(pFile, GoZ_TAG_FLAGS, 1, &m_flags)) return false;
  if (!GoZ_Utils::writeGoZBloc(pFile, GoZ_TAG_POINT_LIST, m_vertexCount, m_vertices)) return false;
  if (!GoZ_Utils::writeGoZBloc(pFile, m_faceType, m_faceCount, m_vertexIndices)) return false;
  if (m_uvs && !GoZ_Utils::writeGoZBloc(pFile, m_uvFaceType, m_faceCount, m_uvs)) return false;
  if (m_mask && !GoZ_Utils::writeGoZBloc(pFile, GoZ_TAG_MASK16_LIST, m_vertexCount, m_mask)) return false;
  if (m_mrgb && !GoZ_Utils::writeGoZBloc(pFile, GoZ_TAG_MRGB_LIST, m_vertexCount, m_mrgb)) return false;
  if (m_groups && !GoZ_Utils::writeGoZBloc(pFile, GoZ_TAG_GROUPS_LIST, m_faceCount, m_groups)) return false;
  if (m_diffuseMap && !GoZ_Utils::writeGoZBloc(pFile, GoZ_TAG_TEXTURE_MAP_PATH, 1, m_diffuseMap)) return false;
  if (m_normalMap && !GoZ_Utils::writeGoZBloc(pFile, GoZ_TAG_NORMAL_MAP_PATH, 1, m_normalMap)) return false;
  if (m_displacementMap && !GoZ_Utils::writeGoZBloc(pFile, GoZ_TAG_DISPLACEMENT_MAP_PATH, 1, m_displacementMap, m_displacementScale)) return false;
  if (m_crease && !GoZ_Utils::writeGoZBloc( pFile, GoZ_TAG_CREASE_LIST, m_faceCount, m_crease )) return false;
   if (!GoZ_Utils::writeGoZBloc(pFile, GoZ_TAG_END_OF_FILE, 0, NULL)) return false;
  GoZ_Utils::closeGoZFile(pFile);
  return true;
}

