"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog"
import { useToast } from "@/components/ui/toast-notification"
import { partnerApi } from "@/lib/api/partners"
import type { PartnerConversionRequest } from "@/lib/api/partners"
import { Loader2, Handshake } from "lucide-react"

interface PartnerConversionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (partnerId: string) => void
}

export function PartnerConversionDialog({ 
  open, 
  onOpenChange, 
  onSuccess 
}: PartnerConversionDialogProps) {
  const [loading, setLoading] = useState(false)
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [showAlreadyPartnerDialog, setShowAlreadyPartnerDialog] = useState(false)
  const [errorMessage, setErrorMessage] = useState("")
  const { toast, ToastContainer } = useToast()
  
  const [formData, setFormData] = useState<PartnerConversionRequest>({
    business_name: "",
    contact_email: "",
    industry: "",
    description: "",
    website: ""
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.business_name || !formData.contact_email) return
    
    // Show confirmation dialog first
    setShowConfirmation(true)
  }

  const handleConfirmConversion = async () => {
    setLoading(true)
    try {
      const partner = await partnerApi.convertToPartner(formData)
      
      toast("Successfully converted to partner! Welcome to the ProtoBox Partner Program.", "success")
      onSuccess(partner.partner_id)
      onOpenChange(false)
      
      // Reset form
      setFormData({
        business_name: "",
        contact_email: "",
        industry: "",
        description: "",
        website: ""
      })
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : "Failed to convert to partner. Please try again."
      
      if (errorMsg.includes("already a partner")) {
        setShowAlreadyPartnerDialog(true)
      } else {
        setErrorMessage(errorMsg)
        toast(errorMsg, "error")
      }
    } finally {
      setLoading(false)
    }
  }

  const handleAlreadyPartnerConfirm = () => {
    // Close both dialogs and refresh
    onOpenChange(false)
    window.location.reload()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Handshake className="w-5 h-5" />
            Become a ProtoBox Partner
          </DialogTitle>
          <DialogDescription>
            Join our partner program to offer integrations to your customers via API.
            Fill out the form below to get started.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="business_name">Business Name *</Label>
              <Input
                id="business_name"
                placeholder="Your company name"
                value={formData.business_name}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  business_name: e.target.value
                }))}
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="contact_email">Contact Email *</Label>
              <Input
                id="contact_email"
                type="email"
                placeholder="partner@yourcompany.com"
                value={formData.contact_email}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  contact_email: e.target.value
                }))}
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="industry">Industry</Label>
              <Input
                id="industry"
                placeholder="e.g., Healthcare, Finance, E-commerce"
                value={formData.industry}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  industry: e.target.value
                }))}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="website">Website</Label>
              <Input
                id="website"
                type="url"
                placeholder="https://yourcompany.com"
                value={formData.website}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  website: e.target.value
                }))}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Tell us about your business and how you plan to use our partner platform..."
                value={formData.description}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  description: e.target.value
                }))}
                rows={3}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button 
              type="submit" 
              disabled={loading || !formData.business_name || !formData.contact_email}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creating Partner Account...
                </>
              ) : (
                <>
                  <Handshake className="w-4 h-4 mr-2" />
                  Become Partner
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
      
      {/* Confirmation Dialog */}
      <ConfirmationDialog
        open={showConfirmation}
        onOpenChange={setShowConfirmation}
        title="Confirm Partner Conversion"
        description={`Are you sure you want to convert "${formData.business_name}" to a ProtoBox Partner? This will enable API access for your customers and cannot be undone.`}
        confirmText="Yes, Become Partner"
        cancelText="Cancel"
        variant="default"
        onConfirm={handleConfirmConversion}
      />
      
      {/* Already Partner Dialog */}
      <ConfirmationDialog
        open={showAlreadyPartnerDialog}
        onOpenChange={setShowAlreadyPartnerDialog}
        title="Already Partner"
        description="You are already a ProtoBox Partner! The page will refresh to show your partner dashboard."
        confirmText="Refresh Page"
        cancelText="Close"
        variant="info"
        onConfirm={handleAlreadyPartnerConfirm}
      />
      
      {/* Toast Container */}
      <ToastContainer />
    </Dialog>
  )
}