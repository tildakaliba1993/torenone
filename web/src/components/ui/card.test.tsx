import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Card, CardContent, CardTitle } from "./card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./table";

describe("Card", () => {
  it("renders its title and content", () => {
    render(
      <Card>
        <CardTitle>Utilisation</CardTitle>
        <CardContent>Rafter 0.78</CardContent>
      </Card>,
    );
    expect(screen.getByText("Utilisation")).toBeTruthy();
    expect(screen.getByText("Rafter 0.78")).toBeTruthy();
  });
});

describe("Table", () => {
  it("renders header and body cells", () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Member</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>Rafter</TableCell>
          </TableRow>
        </TableBody>
      </Table>,
    );
    expect(screen.getByText("Member")).toBeTruthy();
    expect(screen.getByText("Rafter")).toBeTruthy();
  });
});
