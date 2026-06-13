import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "./tabs";

function Example() {
  return (
    <Tabs defaultValue="design">
      <TabsList>
        <TabsTrigger value="design">Design</TabsTrigger>
        <TabsTrigger value="check">Check</TabsTrigger>
      </TabsList>
      <TabsContent value="design">Auto-size</TabsContent>
      <TabsContent value="check">Verify sections</TabsContent>
    </Tabs>
  );
}

describe("Tabs", () => {
  it("shows the default panel and switches on click", async () => {
    render(<Example />);
    expect(screen.getByText("Auto-size")).toBeTruthy();
    expect(screen.queryByText("Verify sections")).toBeNull();

    await userEvent.click(screen.getByRole("tab", { name: "Check" }));
    expect(screen.getByText("Verify sections")).toBeTruthy();
    expect(screen.queryByText("Auto-size")).toBeNull();
  });
});
