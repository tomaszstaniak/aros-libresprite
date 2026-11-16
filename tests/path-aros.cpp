// Host check of base/path.cpp with AmigaDOS paths (built with -D__AROS__).
//   c++ -std=c++20 -D__AROS__ -I<work>/src -I<build>/src tests/path-aros.cpp <work>/src/base/path.cpp
#include "base/path.h"
#include <cstdio>
#include <string>

static int failures;

static void eq(const char* what, const std::string& got, const std::string& want)
{
  if (got != want) {
    std::printf("FAIL %s: got \"%s\", want \"%s\"\n", what, got.c_str(), want.c_str());
    failures++;
  }
}

int main()
{
  using namespace base;
  eq("path of volume file", get_file_path("RAM:pic.png"), "RAM:");
  eq("path of nested file", get_file_path("Work:Art/pic.png"), "Work:Art");
  eq("path of drawer", get_file_path("Work:Art/Sub"), "Work:Art");
  eq("path of volume", get_file_path("Work:"), "Work:");
  eq("path of relative", get_file_path("pic.png"), "");
  eq("name of volume file", get_file_name("RAM:pic.png"), "pic.png");
  eq("name of nested file", get_file_name("Work:Art/pic.png"), "pic.png");
  eq("extension", get_file_extension("RAM:pic.png"), "png");
  eq("extension none", get_file_extension("RAM:noext"), "");
  eq("extension of volume", get_file_extension("My.Disk:file"), "");
  eq("title", get_file_title("RAM:pic.png"), "pic");
  eq("replace extension", replace_extension("RAM:pic.png", "gif"), "RAM:pic.gif");
  eq("join volume", join_path("RAM:", "pic.png"), "RAM:pic.png");
  eq("join drawer", join_path("Work:Art", "pic.png"), "Work:Art/pic.png");
  eq("join slash", join_path("Work:Art/", "pic.png"), "Work:Art/pic.png");
  eq("join relative", join_path("data", "gui.xml"), "data/gui.xml");
  eq("unix path", get_file_path("/usr/share/x.png"), "/usr/share");
  std::printf(failures ? "result: fail (%d)\n" : "result: pass\n", failures);
  return failures != 0;
}

// path.cpp's other dependencies, not exercised here.
namespace base {
std::string string_to_lower(const std::string& s) { return s; }
std::string get_canonical_path(const std::string& s) { return s; }
}
