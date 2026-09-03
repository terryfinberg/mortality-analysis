-- Number figure and table captions, for writers that do not do it themselves.
--
-- Pandoc's LaTeX and typst writers emit \begin{figure}\caption{...} and
-- #figure(caption: ...), and the typesetter numbers those. The docx and html
-- writers do not: a caption there is just a styled paragraph, so a submission
-- built for Word arrives with five unnumbered images and prose that says
-- "Figure 2 shows the same interval band by band".
--
-- This filter is therefore applied to the docx and html paths only. Applying it
-- to LaTeX as well would produce "Figure 1: Figure 1: ...", which is why
-- export.py decides per target rather than always running it.
--
-- The manuscript's captions carry no number of their own, so numbering lives in
-- exactly one place: here.

local figure_number = 0
local table_number = 0

local function prefix(caption, label)
  -- An empty caption stays empty. A figure with no caption is a layout
  -- element, and "Figure 3:" alone on a line is worse than nothing.
  if not caption or #caption == 0 then
    return caption
  end
  local first = caption[1]
  if first.t == "Plain" or first.t == "Para" then
    -- Inserted back to front: the label must end up before the space it is
    -- separated from the caption by.
    table.insert(first.content, 1, pandoc.Space())
    table.insert(first.content, 1, pandoc.Str(label))
  end
  return caption
end

function Figure(fig)
  figure_number = figure_number + 1
  fig.caption.long = prefix(fig.caption.long, "Figure " .. figure_number .. ".")
  return fig
end

function Table(tbl)
  table_number = table_number + 1
  tbl.caption.long = prefix(tbl.caption.long, "Table " .. table_number .. ".")
  return tbl
end

-- Figures must be numbered in reading order, and Table nodes must not consume
-- figure numbers. Pandoc walks blocks in document order within a single filter
-- pass, so returning both handlers in one table preserves that order.
return { { Figure = Figure, Table = Table } }
