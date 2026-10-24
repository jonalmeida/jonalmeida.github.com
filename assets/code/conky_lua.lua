--[[ this script combines the background drawing lua (originally by londonali1010, modified by VinDSL)
with a script that emulates only the gradient bars portion of the script by wlourf
call in conkyrc above TEXT like so
lua_load /path to file/filename.lua
lua_draw_hook_pre draw_lua
]]
require 'cairo'
function conky_draw_lua()
if conky_window == nil then return end
local cs = cairo_xlib_surface_create(conky_window.display, conky_window.drawable, conky_window.visual, conky_window.width, conky_window.height)
cr = cairo_create(cs)
local updates=tonumber(conky_parse('${updates}'))
if updates>5 then
--#########################################################################################################
--#########################################################################################################
--background setup -- make sure this comes first-----------
--settings={--CONKY BACKGROUND
--corner_r=50,--corner radius
--bg_color={0x222222,0.9},--color and alpha inside {}
--bg_height=-42,--negative number reduces height of bg
--w=conky_window.width,
--h=conky_window.height,
--};background(settings)
--end background setup-------------------------------------
--Line 1 settings
local a_arg=conky_parse('${cpu}')
local a_thick=10
local a_red=0
local a_green=0
local a_blue=0
local a_alpha=1
local a_start=10
--line 1 settings end  
local a_num=tonumber(a_arg)
--line 1 background

--line 1 title
cairo_rotate (cr,0*math.pi/180)
cairo_show_text (cr, "CPU");
cairo_rotate (cr, -90*math.pi/180)

bar_adjust=-2

--bar setup------------------------------------------------
settings={--CPU GRAPH CPU1
number=tonumber(conky_parse("${cpu cpu1}")),--conky object to read
number_max=100,--max value of conky object
bar_startx=-300,--x coordinate
bar_starty=25+bar_adjust,--y coordinate
divisions=38,--number of blocks
div_width=2,--horizontal size
div_height=25,--vertical size
div_gap=1,--space between bits
bg_color={0xFFFFFF,0.25},--background color, color and alpha inside {}
st_color={0x00FF00,1},--start color for gradient, green
mid_color={0xFFFF00,1},--middle color for gradient, yellow
end_color={0xFF0000,1},--end color for gradient
};bars(settings)
settings={--CPU GRAPH CPU1
number=tonumber(conky_parse("${cpu cpu2}")),--conky object to read
number_max=100,--max value of conky object
bar_startx=-300,--x coordinate
bar_starty=90+bar_adjust,--y coordinate
divisions=38,--number of blocks
div_width=2,--horizontal size
div_height=25,--vertical size
div_gap=1,--space between bits
bg_color={0xFFFFFF,0.25},--background color, color and alpha inside {}
st_color={0x00FF00,1},--start color for gradient, green
mid_color={0xFFFF00,1},--middle color for gradient, yellow
end_color={0xFF0000,1},--end color for gradient
};bars(settings)
settings={--CPU GRAPH CPU1
number=tonumber(conky_parse("${cpu cpu3}")),--conky object to read
number_max=100,--max value of conky object
bar_startx=-300,--x coordinate
bar_starty=160+bar_adjust,--y coordinate
divisions=38,--number of blocks
div_width=2,--horizontal size
div_height=25,--vertical size
div_gap=1,--space between bits
bg_color={0xFFFFFF,0.25},--background color, color and alpha inside {}
st_color={0x00FF00,1},--start color for gradient, green
mid_color={0xFFFF00,1},--middle color for gradient, yellow
end_color={0xFF0000,1},--end color for gradient
};bars(settings)
settings={--CPU GRAPH CPU1
number=tonumber(conky_parse("${cpu cpu4}")),--conky object to read
number_max=100,--max value of conky object
bar_startx=-300,--x coordinate
bar_starty=225+bar_adjust,--y coordinate
divisions=38,--number of blocks
div_width=2,--horizontal size
div_height=25,--vertical size
div_gap=1,--space between bits
bg_color={0xFFFFFF,0.25},--background color, color and alpha inside {}
st_color={0x00FF00,1},--start color for gradient, green
mid_color={0xFFFF00,1},--middle color for gradient, yellow
end_color={0xFF0000,1},--end color for gradient
};bars(settings)
--copy and paste above for new bar-------------------------
--#########################################################################################################
--#########################################################################################################
end-- if updates>5
cairo_destroy(cr)
cairo_surface_destroy(cs)
cr=nil
end-- end main function
function rgb_to_r_g_b(col_a)
return ((col_a[1] / 0x10000) % 0x100) / 255., ((col_a[1] / 0x100) % 0x100) / 255., (col_a[1] % 0x100) / 255., col_a[2]
end
function bars(t)
local bar_startx=t.bar_startx
local bar_starty=t.bar_starty
local divisions=t.divisions
local div_width=t.div_width
local div_height=t.div_height
local div_gap=t.div_gap
local br,bg,bb,ba=rgb_to_r_g_b(t.bg_color)
local sr,sg,sb,sa=rgb_to_r_g_b(t.st_color)
local mr,mg,mb,ma=rgb_to_r_g_b(t.mid_color)
local er,eg,eb,ea=rgb_to_r_g_b(t.end_color)
if t.number==nil then number=0 else number=t.number end
local number_max=t.number_max
local number_divs=(number/number_max)*divisions
cairo_set_line_width (cr,div_width)
for i=1,divisions do
if i<(divisions/2) and i<=number_divs then
colr=((mr-sr)*(i/(divisions/2)))+sr
colg=((mg-sg)*(i/(divisions/2)))+sg
colb=((mb-sb)*(i/(divisions/2)))+sb
cola=((ma-sa)*(i/(divisions/2)))+sa
elseif i>=(divisions/2) and i<=number_divs then
colr=((er-mr)*((i-(divisions/2))/(divisions/2)))+mr
colg=((eg-mg)*((i-(divisions/2))/(divisions/2)))+mg
colb=((eb-mb)*((i-(divisions/2))/(divisions/2)))+mb
cola=((ea-ma)*((i-(divisions/2))/(divisions/2)))+ma
else
colr=br
colg=bg
colb=bb
cola=ba
end
cairo_set_source_rgba (cr,colr,colg,colb,cola)
cairo_move_to (cr,bar_startx+((div_width+div_gap)*i-1),bar_starty)
cairo_rel_line_to (cr,0,div_height)
cairo_stroke (cr)
end
end--function bars
function background(t)
local corner_r=t.corner_r
local br,bg,bb,ba=rgb_to_r_g_b(t.bg_color)
local v=t.bg_height
local h=t.h
local w=t.w
cairo_move_to(cr,corner_r,0)
cairo_line_to(cr,w-corner_r,0)
cairo_curve_to(cr,w,0,w,0,w,corner_r)
cairo_line_to(cr,w,h+v-corner_r)
cairo_curve_to(cr,w,h+v,w,h+v,w-corner_r,h+v)
cairo_line_to(cr,corner_r,h+v)
cairo_curve_to(cr,0,h+v,0,h+v,0,h+v-corner_r)
cairo_line_to(cr,0,corner_r)
cairo_curve_to(cr,0,0,0,0,corner_r,0)
cairo_close_path(cr)
cairo_set_source_rgba(cr,br,bg,bb,ba)
cairo_fill(cr)
end--function background
