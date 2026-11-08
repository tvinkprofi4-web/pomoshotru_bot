
-- Test Roblox Lua Script
local Players = game:GetService('Players')
local function onPlayerAdded(player)
    print('Player joined:', player.Name)
end
Players.PlayerAdded:Connect(onPlayerAdded)
