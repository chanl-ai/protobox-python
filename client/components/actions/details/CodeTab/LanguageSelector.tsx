"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { useActionForm } from "../FormProvider"
import { Code, Terminal, Database, FileCode } from "lucide-react"

const languageOptions = [
  { value: "python", label: "Python", icon: Code, description: "Execute Python scripts with pip packages" },
  { value: "javascript", label: "JavaScript", icon: FileCode, description: "Run Node.js JavaScript code with npm packages" },
  { value: "sql", label: "SQL", icon: Database, description: "Execute SQL queries against databases" },
  { value: "shell", label: "Shell", icon: Terminal, description: "Run bash/shell commands and scripts" }
]

export function LanguageSelector() {
  const { form } = useActionForm()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Programming Language</CardTitle>
        <CardDescription>
          Select the programming language for your code action
        </CardDescription>
      </CardHeader>
      <CardContent>
        <FormField
          control={form.control}
          name="codeLanguage"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Language</FormLabel>
              <Select onValueChange={field.onChange} defaultValue={field.value}>
                <FormControl>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select programming language" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {languageOptions.map((language) => {
                    const Icon = language.icon
                    return (
                      <SelectItem key={language.value} value={language.value}>
                        <div className="flex items-center space-x-2">
                          <Icon className="h-4 w-4" />
                          <span>{language.label}</span>
                        </div>
                      </SelectItem>
                    )
                  })}
                </SelectContent>
              </Select>
              <FormDescription>
                {languageOptions.find(lang => lang.value === field.value)?.description || 
                 "Choose the programming language for your action's code"}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
      </CardContent>
    </Card>
  )
}