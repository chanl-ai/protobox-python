"use client";

import type { LucideIcon } from "lucide-react";
import {
  Banknote,
  BarChart,
  BookOpen,
  Brain,
  Cloud,
  Code,
  CreditCard,
  Database,
  Factory,
  Fingerprint,
  Gamepad2,
  Globe,
  Home,
  Lock,
  Menu,
  MessageSquare,
  Plane,
  Settings,
  Shield,
  ShoppingCart,
  Sparkle,
  Truck,
  Users,
  X,
} from "lucide-react";
import { useState } from "react";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
} from "@/components/ui/navigation-menu";

interface Solution {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
}

const DATA_SOLUTIONS: Solution[] = [
  {
    title: "First solution",
    description: "Vestibulum scelerisque quis nisl ut convallis.",
    href: "#",
    icon: Cloud,
  },
  {
    title: "Another solution",
    description: "Curabitur vehicula malesuada enim a cursus.",
    href: "#",
    icon: Lock,
  },
  {
    title: "And a third solution",
    description: "Proin aliquam feugiat lobortis.",
    href: "#",
    icon: Fingerprint,
  },
  {
    title: "And a fourth solution",
    description: "Donec nec sapien nec dolor.",
    href: "#",
    icon: Cloud,
  },
];

interface Platfrom {
  title: string;
  href: string;
  icon: LucideIcon;
}

const DATA_PLATFORM_CASE: Platfrom[] = [
  {
    title: "Banking",
    href: "#",
    icon: CreditCard,
  },
  {
    title: "Fintech",
    href: "#",
    icon: Banknote,
  },
  {
    title: "E-commerce",
    href: "#",
    icon: ShoppingCart,
  },
  {
    title: "Travel & Hospitality",
    href: "#",
    icon: Plane,
  },
  {
    title: "Real Estate",
    href: "#",
    icon: Home,
  },
  {
    title: "Gaming",
    href: "#",
    icon: Gamepad2,
  },
  {
    title: "Manufacturing",
    href: "#",
    icon: Factory,
  },
  {
    title: "Logistics",
    href: "#",
    icon: Truck,
  },
];

interface Resource {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
}

const DATA_RESOURCES: Resource[] = [
  {
    title: "AI Powered",
    description: "Explore AI-powered resources",
    href: "#",
    icon: Sparkle,
  },
  {
    title: "AI Development",
    description: "Tools and frameworks for AI development",
    href: "#",
    icon: Code,
  },
  {
    title: "Machine Learning",
    description: "Resources for machine learning enthusiasts",
    href: "#",
    icon: Brain,
  },
  {
    title: "Data Management",
    description: "Best practices for data management",
    href: "#",
    icon: Database,
  },
  {
    title: "Cloud AI",
    description: "Cloud-based AI solutions",
    href: "#",
    icon: Cloud,
  },
  {
    title: "AI Security",
    description: "Secure your AI applications",
    href: "#",
    icon: Shield,
  },
  {
    title: "AI Configuration",
    description: "Configure AI systems effectively",
    href: "#",
    icon: Settings,
  },
  {
    title: "AI Analytics",
    description: "Analyze AI performance metrics",
    href: "#",
    icon: BarChart,
  },
  {
    title: "Global AI Trends",
    description: "Stay updated with global AI trends",
    href: "#",
    icon: Globe,
  },
  {
    title: "AI Community",
    description: "Join the AI community",
    href: "#",
    icon: Users,
  },
  {
    title: "AI Learning",
    description: "Learn AI from the best resources",
    href: "#",
    icon: BookOpen,
  },
  {
    title: "AI Support",
    description: "Get support for AI-related queries",
    href: "#",
    icon: MessageSquare,
  },
];

const Navbar7 = () => {
  const [open, setOpen] = useState(false);
  return (
    <section className="bg-background inset-x-0 top-0 z-20">
      <div className="container px-4 sm:px-6 md:px-8 lg:px-40 xl:px-52">
        <NavigationMenu className="min-w-full">
          <div className="flex w-full items-center justify-between gap-12 py-4">
            <a href="#" className="flex items-center gap-2">
              <img
                src="https://deifkwefumgah.cloudfront.net/shadcnblocks/block/logos/shadcnblockscom-icon.svg"
                className="max-h-8"
                alt="Shadcn UI Navbar"
              />
              <span className="text-lg font-semibold tracking-tighter">
                Shadcnblocks.com
              </span>
            </a>
            <NavigationMenuList className="hidden lg:flex">
              <NavigationMenuItem>
                <NavigationMenuTrigger>Platform</NavigationMenuTrigger>
                <NavigationMenuContent className="min-w-[760px] p-4">
                  <div className="flex items-start justify-between">
                    <div className="max-w-[760px] flex-1">
                      <div className="text-muted-foreground text-xs tracking-widest">
                        Solutions
                      </div>
                      <div className="grid grid-rows-1 gap-6">
                        {DATA_SOLUTIONS.map((solution, index) => (
                          <NavigationMenuLink
                            key={index}
                            href={solution.href}
                            className="group flex flex-row items-center first:mt-4 hover:bg-transparent"
                          >
                            <div className="bg-muted mr-4 rounded-lg p-4 shadow-sm">
                              <solution.icon className="text-muted-foreground fade-in group-hover:text-foreground size-6 transition-all" />
                            </div>
                            <div className="flex flex-col gap-1 text-sm">
                              <div className="text-foreground font-medium">
                                {solution.title}
                              </div>
                              <div className="text-muted-foreground text-sm font-normal">
                                {solution.description}
                              </div>
                            </div>
                          </NavigationMenuLink>
                        ))}
                      </div>
                    </div>
                    <div className="max-w-[760px] flex-1">
                      <div className="text-muted-foreground text-xs tracking-widest">
                        By Use Case
                      </div>
                      <div className="mt-4 gap-6">
                        {DATA_PLATFORM_CASE.map((solution, index) => (
                          <NavigationMenuLink
                            key={index}
                            href={solution.href}
                            className="group flex flex-row items-center hover:bg-transparent"
                          >
                            <div className="bg-muted mr-4 rounded-lg p-2 shadow-sm">
                              <solution.icon className="text-muted-foreground fade-in group-hover:text-foreground size-4 transition-all" />
                            </div>
                            <div className="flex flex-col gap-1">
                              <div className="text-sm font-medium">
                                {solution.title}
                              </div>
                            </div>
                          </NavigationMenuLink>
                        ))}
                      </div>
                    </div>
                  </div>
                </NavigationMenuContent>
              </NavigationMenuItem>
              <NavigationMenuItem>
                <NavigationMenuTrigger>Resources</NavigationMenuTrigger>
                <NavigationMenuContent className="w-full min-w-[820px] p-4">
                  <div className="grid grid-cols-3 gap-6">
                    {DATA_RESOURCES.map((solution, index) => (
                      <NavigationMenuLink
                        key={index}
                        href={solution.href}
                        className="group flex flex-row items-center hover:bg-transparent"
                      >
                        <div className="bg-muted mr-4 rounded-lg p-4 shadow-sm">
                          <solution.icon className="text-muted-foreground fade-in group-hover:text-foreground size-6 transition-all" />
                        </div>
                        <div className="text-muted-foreground flex flex-col gap-1 text-sm font-normal">
                          <div className="text-foreground font-medium">
                            {solution.title}
                          </div>
                          <div className="text-muted-foreground font-normal">
                            {solution.description}
                          </div>
                        </div>
                      </NavigationMenuLink>
                    ))}
                  </div>
                </NavigationMenuContent>
              </NavigationMenuItem>
              <Button variant="ghost">Developer</Button>
            </NavigationMenuList>
            <div className="hidden items-center gap-4 lg:flex">
              <Button variant="ghost">Sign in</Button>
              <Button>Get Started</Button>
            </div>
            <div className="flex items-center gap-4 lg:hidden">
              <Button
                variant="outline"
                size="icon"
                aria-label="Main Menu"
                onClick={() => {
                  if (open) {
                    setOpen(false);
                  } else {
                    setOpen(true);
                  }
                }}
              >
                {!open && <Menu className="size-4" />}
                {open && <X className="size-4" />}
              </Button>
            </div>
          </div>

          {/* Mobile Menu (Root) */}
          {open && (
            <div className="border-border bg-background absolute inset-0 top-[72px] flex h-[calc(100vh-72px)] w-full flex-col overflow-scroll border-t lg:hidden">
              <Accordion type="single" collapsible className="w-full">
                <AccordionItem
                  value="platform"
                  className="border-b-2 border-dashed"
                >
                  <AccordionTrigger className="px-2 py-4 text-left hover:no-underline">
                    Platform
                  </AccordionTrigger>
                  <AccordionContent className="px-2 pb-4">
                    <div className="space-y-6">
                      <div>
                        <div className="text-muted-foreground mb-4 text-xs uppercase tracking-widest">
                          Solutions
                        </div>
                        <div className="space-y-4">
                          {DATA_SOLUTIONS.map((solution, index) => (
                            <a
                              key={index}
                              href={solution.href}
                              className="hover:bg-muted group flex items-center gap-4 rounded-lg p-2"
                            >
                              <div className="bg-muted rounded-lg p-2 shadow-sm">
                                <solution.icon className="text-muted-foreground group-hover:text-foreground size-4 transition-all" />
                              </div>
                              <div className="flex-1">
                                <div className="text-foreground text-sm font-medium">
                                  {solution.title}
                                </div>
                                <div className="text-muted-foreground text-xs">
                                  {solution.description}
                                </div>
                              </div>
                            </a>
                          ))}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground mb-4 text-xs uppercase tracking-widest">
                          By Use Case
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          {DATA_PLATFORM_CASE.map((useCase, index) => (
                            <a
                              key={index}
                              href={useCase.href}
                              className="hover:bg-muted group flex items-center gap-2 rounded-lg p-2"
                            >
                              <div className="bg-muted rounded-lg p-1.5 shadow-sm">
                                <useCase.icon className="text-muted-foreground group-hover:text-foreground size-3 transition-all" />
                              </div>
                              <div className="truncate text-sm font-medium">
                                {useCase.title}
                              </div>
                            </a>
                          ))}
                        </div>
                      </div>
                    </div>
                  </AccordionContent>
                </AccordionItem>

                <AccordionItem
                  value="resources"
                  className="border-b-2 border-dashed"
                >
                  <AccordionTrigger className="px-2 py-4 text-left hover:no-underline">
                    Resources
                  </AccordionTrigger>
                  <AccordionContent className="px-2 pb-4">
                    <div className="space-y-3">
                      {DATA_RESOURCES.map((resource, index) => (
                        <a
                          key={index}
                          href={resource.href}
                          className="hover:bg-muted group flex items-center gap-4 rounded-lg p-2"
                        >
                          <div className="bg-muted rounded-lg p-2 shadow-sm">
                            <resource.icon className="text-muted-foreground group-hover:text-foreground size-4 transition-all" />
                          </div>
                          <div className="flex-1">
                            <div className="text-foreground text-sm font-medium">
                              {resource.title}
                            </div>
                            <div className="text-muted-foreground text-xs">
                              {resource.description}
                            </div>
                          </div>
                        </a>
                      ))}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
              <a
                href="#"
                className="w-full border-y-2 border-dashed px-2 py-4 text-left text-sm font-medium"
              >
                Developer
              </a>

              <div className="mx-8 mt-auto flex flex-col gap-4 py-12">
                <span className="text-center">
                  Existing Customer? <b>Login</b>
                </span>
                <Button className="relative" size="lg">
                  Start now
                </Button>
              </div>
            </div>
          )}
        </NavigationMenu>
      </div>
    </section>
  );
};

export { Navbar7 };
