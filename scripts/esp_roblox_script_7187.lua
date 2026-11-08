
local Rayfield = loadstring(game:HttpGet("https://sirius.menu/rayfield"))()
local Window = Rayfield:CreateWindow({Name = "ESP Hub", LoadingTitle = "Loading...", LoadingSubtitle = "by AI"})
local Tab = Window:CreateTab("ESP", 4483362458)
Tab:CreateToggle({Name = "Box ESP", CurrentValue = false, Callback = function(v) print(v) end})
