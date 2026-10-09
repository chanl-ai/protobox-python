"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Bell, Calendar, Clock } from "lucide-react"

export type GoogleCalendarAdvancedSettings = {
  defaultCalendar: string
  timezone: string
  workingHoursStart: string
  workingHoursEnd: string
  bufferTime: string
  defaultDuration: string
  autoDeclineConflicts: boolean
  weekendsAvailable: boolean
  defaultLocation: string
  defaultVisibility: string
  defaultReminder: string
  defaultReminderMethod: string
  showDeclinedEvents: boolean
  colorCoding: boolean
}

export type GoogleCalendarIntegrationData = {
  calendars?: Array<{ id: string; summary: string; primary?: boolean }>
  timezones?: Array<{ value: string; label: string }>
} | null

export interface GoogleCalendarIntegrationSettingsProps {
  settings: GoogleCalendarAdvancedSettings
  onChange: (patch: Partial<GoogleCalendarAdvancedSettings>) => void
  integrationData: GoogleCalendarIntegrationData
}

export function GoogleCalendarIntegrationSettings({
  settings,
  onChange,
  integrationData,
}: GoogleCalendarIntegrationSettingsProps) {
  return (
    <>
      <div className="space-y-4">
        <h3 className="text-sm font-medium flex items-center gap-2">
          <Calendar className="h-4 w-4" />
          Calendar Preferences
        </h3>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="defaultCalendar">Primary Calendar</Label>
            <Select
              value={settings.defaultCalendar}
              onValueChange={(value) => onChange({ defaultCalendar: value })}
            >
              <SelectTrigger id="defaultCalendar">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {integrationData?.calendars ? (
                  integrationData.calendars.map((cal) => (
                    <SelectItem key={cal.id} value={cal.id}>
                      {cal.summary} {cal.primary && "(Primary)"}
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="primary">Primary Calendar</SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="timezone">Time Zone</Label>
            <Select
              value={settings.timezone}
              onValueChange={(value) => onChange({ timezone: value })}
            >
              <SelectTrigger id="timezone">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {integrationData?.timezones ? (
                  integrationData.timezones.map((tz) => (
                    <SelectItem key={tz.value} value={tz.value}>
                      {tz.label}
                    </SelectItem>
                  ))
                ) : (
                  <>
                    <SelectItem value="America/New_York">Eastern Time</SelectItem>
                    <SelectItem value="America/Chicago">Central Time</SelectItem>
                    <SelectItem value="America/Denver">Mountain Time</SelectItem>
                    <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                  </>
                )}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-sm font-medium flex items-center gap-2">
          <Clock className="h-4 w-4" />
          Availability Settings
        </h3>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Working Hours</Label>
            <div className="flex gap-2 items-center">
              <Input
                type="time"
                value={settings.workingHoursStart}
                onChange={(e) => onChange({ workingHoursStart: e.target.value })}
                className="flex-1"
              />
              <span className="text-sm text-muted-foreground">to</span>
              <Input
                type="time"
                value={settings.workingHoursEnd}
                onChange={(e) => onChange({ workingHoursEnd: e.target.value })}
                className="flex-1"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="bufferTime">Buffer Between Meetings</Label>
            <Select
              value={settings.bufferTime}
              onValueChange={(value) => onChange({ bufferTime: value })}
            >
              <SelectTrigger id="bufferTime">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="0">No buffer</SelectItem>
                <SelectItem value="5">5 minutes</SelectItem>
                <SelectItem value="10">10 minutes</SelectItem>
                <SelectItem value="15">15 minutes</SelectItem>
                <SelectItem value="30">30 minutes</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="defaultDuration">Default Meeting Duration</Label>
            <Select
              value={settings.defaultDuration}
              onValueChange={(value) => onChange({ defaultDuration: value })}
            >
              <SelectTrigger id="defaultDuration">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="15">15 minutes</SelectItem>
                <SelectItem value="30">30 minutes</SelectItem>
                <SelectItem value="45">45 minutes</SelectItem>
                <SelectItem value="60">1 hour</SelectItem>
                <SelectItem value="90">1.5 hours</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="autoDecline">Auto-decline conflicts</Label>
              <Switch
                id="autoDecline"
                checked={settings.autoDeclineConflicts}
                onCheckedChange={(checked) => onChange({ autoDeclineConflicts: checked })}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="weekends">Available on weekends</Label>
              <Switch
                id="weekends"
                checked={settings.weekendsAvailable}
                onCheckedChange={(checked) => onChange({ weekendsAvailable: checked })}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-sm font-medium flex items-center gap-2">
          <Bell className="h-4 w-4" />
          Meeting Defaults
        </h3>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="defaultLocation">Default Location</Label>
            <Input
              id="defaultLocation"
              placeholder="e.g., Zoom, Conference Room A"
              value={settings.defaultLocation}
              onChange={(e) => onChange({ defaultLocation: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="defaultVisibility">Default Visibility</Label>
            <Select
              value={settings.defaultVisibility}
              onValueChange={(value) => onChange({ defaultVisibility: value })}
            >
              <SelectTrigger id="defaultVisibility">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="default">Default</SelectItem>
                <SelectItem value="public">Public</SelectItem>
                <SelectItem value="private">Private</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Default Reminder</Label>
            <div className="flex gap-2">
              <Select
                value={settings.defaultReminder}
                onValueChange={(value) => onChange({ defaultReminder: value })}
              >
                <SelectTrigger className="flex-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">No reminder</SelectItem>
                  <SelectItem value="5">5 minutes</SelectItem>
                  <SelectItem value="10">10 minutes</SelectItem>
                  <SelectItem value="15">15 minutes</SelectItem>
                  <SelectItem value="30">30 minutes</SelectItem>
                  <SelectItem value="60">1 hour</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={settings.defaultReminderMethod}
                onValueChange={(value) => onChange({ defaultReminderMethod: value })}
              >
                <SelectTrigger className="w-[120px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="popup">Popup</SelectItem>
                  <SelectItem value="email">Email</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="showDeclined">Show declined events</Label>
              <Switch
                id="showDeclined"
                checked={settings.showDeclinedEvents}
                onCheckedChange={(checked) => onChange({ showDeclinedEvents: checked })}
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="colorCoding">Color code by calendar</Label>
              <Switch
                id="colorCoding"
                checked={settings.colorCoding}
                onCheckedChange={(checked) => onChange({ colorCoding: checked })}
              />
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
